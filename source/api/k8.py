import os
import shutil
import tempfile
import collections
import json
import urllib
import base64
import string
import collections
import urllib.parse
import requests
from datetime import datetime, timedelta
import django.conf

import analitico.utilities
from rest_framework import status

from analitico import AnaliticoException, logger
from analitico.utilities import (
    save_json,
    save_text,
    read_text,
    get_dict_dot,
    set_dict_dot,
    subprocess_run,
    read_json,
    copy_directory,
    id_generator,
    size_to_bytes,
    cpu_unit_to_fractional,
)
from api.factory import factory
from api.models import ItemMixin, Job, Recipe, Model, Workspace
from api.models.job import generate_job_id
from api.models.notebook import nb_extract_serverless

K8_DEFAULT_NAMESPACE = "cloud"  # service.cloud.analitico.ai
K8_DEFAULT_CONCURRENCY = 20  # concurrent connection per docker

K8_STAGE_PRODUCTION = "production"  # a knative service deployed for general production purpose
K8_STAGE_STAGING = "staging"  # a development service

# directory where the template used to dockerize notebooks is stored
K8_TEMPLATE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../serverless/templates"))
assert os.path.isdir(K8_TEMPLATE_DIR)

# directory where the template used to dockerize jobs is stored
K8_JOB_TEMPLATE_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "../../serverless/templates/analitico-client")
)
assert os.path.isdir(K8_JOB_TEMPLATE_DIR)

SOURCE_TEMPLATE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../source"))
assert os.path.isdir(SOURCE_TEMPLATE_DIR)


def k8_normalize_name(name: str):
    return name.lower().replace("_", "-")


def kubectl(namespace: str, action: str, resource: str, output: str = "json", args: [] = []) -> (str, str):
    """ Exec operation on Kubernetes using Kubectl command """
    try:
        return subprocess_run(["kubectl", action, "--namespace", namespace, resource, "--output", output, *args])
    except Exception as exec:
        raise AnaliticoException(
            f"Resource not found or invalid request", status_code=status.HTTP_404_NOT_FOUND
        ) from exec


def k8_wait_for_condition(namespace: str, resource: str, condition: str, labels: str = None, timeout: int = 60):
    """ 
    Wait the resource for the given condition. Command fails when the timeout expires. 
    
    Parameters
    ----------
    namespace : str
        Kubernetes resource namespace. Eg: cloud
    resource : str
        Kubernetes resource group and name with the following sintax: resource.group/resource.name.
        Eg: kservice/api-staging
        If labels are provided resource is only resource.group
    condition : str
        The pod condition to wait for:
            - delete
            - condition=condition-name eg, "condition=Ready"
    labels : str
        Comma separeted key=value labels
        Eg: analitico.ai/service=jupyer,app=jupyer-ws-test
    timeout : int, optional
        Timeout in seconds before give up.
        Zero-value means check once and don"t wait.

    Returns
    -------
    Tuple (stdout, stderr)
        from the run command
    """
    try:
        selector = "--selector" if labels is not None else ""
        return subprocess_run(
            [
                "kubectl",
                "wait",
                "-n",
                namespace,
                resource,
                selector,
                labels,
                f"--for={condition}",
                f"--timeout={timeout}s",
            ]
        )
    except Exception as exec:
        raise AnaliticoException(
            f"The resource {resource} cannot be retrieved or not found", status_code=status.HTTP_404_NOT_FOUND
        ) from exec


def get_image_commit_sha():
    """ 
    Return the git commit SHA the running image is built from. 
    If not set is returned the `latest` tag.
    """
    commit_sha = os.environ.get("ANALITICO_COMMIT_SHA", None)
    if not commit_sha:
        commit_sha = "latest"
        msg = "get_image_commit_sha - ANALITICO_COMMIT_SHA is not defined, will build using `latest` tag instead."
        logger.warning(msg)
    return commit_sha


def k8_build_v2(item: ItemMixin, target: ItemMixin, job_data: dict = None, push=True) -> dict:
    """
    Takes an item, extracts its notebook then extracts python code marked for deployment
    from the notebook. Then takes a template directory and applies customizations to it.
    Calls Google Build to build the docker and then publish the docker to a private registry.
    Returns a dictionary with information on the built docker and adds the same dictionary to
    the job as well. Logs operations to the job while they are being performed.
    """
    assert item
    assert target

    item_id_slug = k8_normalize_name(item.id)
    target_id_slug = k8_normalize_name(target.id)

    with tempfile.TemporaryDirectory(prefix="build_") as tmpdirname:
        # copy items from the template used to dockerize
        copy_directory(K8_JOB_TEMPLATE_DIR, tmpdirname)

        # copy current contents of this recipe"s files on the attached drive to our docker directory
        item_drive_path = os.environ.get("ANALITICO_ITEM_PATH", None)
        if item_drive_path:
            copy_directory(item_drive_path, tmpdirname)
        else:
            logger.error(
                f"k8_build can't find environment variable ANALITICO_ITEM_PATH and cannot copy source item files."
            )

        # copy s24 helper methods
        # TODO /s24 need to be built into standalone libraries
        copy_directory(os.path.join(SOURCE_TEMPLATE_DIR, "s24"), os.path.join(tmpdirname, "libraries", "s24"))

        # extract code from notebook
        notebook_name = job_data.get("notebook", "notebook.ipynb") if job_data else "notebook.ipynb"
        notebook = read_json(os.path.normpath(f"{tmpdirname}/{notebook_name}"))
        if not notebook:
            raise AnaliticoException(
                f"Item '{item.id}' does not contain a notebook that can be built, please add a notebook."
            )

        analitico_drive = os.environ.get("ANALITICO_DRIVE", None)
        if analitico_drive:
            # save notebook for inspection and
            # keep the notebook name into the model
            target_drive_path = os.path.join(analitico_drive, f"{target.type}s/{target.id}")
            # eg: /mnt/analitico-drive/models/ml_123456/my-folder/my-notebook.ipynb
            notebook_fullname = os.path.normpath(f"{target_drive_path}/{notebook_name}")
            os.makedirs(os.path.dirname(notebook_fullname), exist_ok=True)
            save_json(notebook, notebook_fullname, indent=2)
            target.set_attribute("notebook", notebook_name)
        else:
            logger.error(
                f"k8_build can't find environment variable ANALITICO_DRIVE and cannot save the notebook file for inspections."
            )

        # extract source code and scripting from notebook
        source, script = nb_extract_serverless(notebook)
        logger.info(f"scripts:{script}\nsource:\n{source}")

        # overwrite template files
        save_json(notebook, os.path.join(tmpdirname, "notebook.ipynb"), indent=2)
        save_text(source, os.path.join(tmpdirname, "notebook.py"))
        save_text(script, os.path.join(tmpdirname, "notebook.sh"))

        # check if the recipe produced metadata.json
        metadata_filename = os.path.join(tmpdirname, "metadata.json")
        if os.path.isfile(metadata_filename):
            metadata = read_json(metadata_filename)
            target.set_attribute("metadata", metadata)

        # docker build docker image need to be lowercase
        image_name = f"eu.gcr.io/analitico-api/{item_id_slug}:{target_id_slug}"

        # build docker image, save id temporary file...
        docker_build_args = ["docker", "build", "-t", image_name, tmpdirname]
        subprocess_run(docker_build_args, cwd=tmpdirname)

        if push:
            # push docker image to registry
            docker_push_args = ["docker", "push", image_name]
            subprocess_run(docker_push_args, timeout=600)  # 10 minutes to upload image

    # retrieve docker information, output is json, parse and add basic info to docker dict
    docker_inspect_args = ["docker", "inspect", image_name]
    docker_inspect, _ = subprocess_run(docker_inspect_args)
    docker_inspect = docker_inspect[0]

    if push:
        image = docker_inspect["RepoDigests"][0]
        image_id = image[image.find("sha256:") :]
    else:
        image = image_name
        image_id = target_id_slug

    # save docker information inside item and job
    docker = collections.OrderedDict()
    docker["type"] = "analitico/docker"
    docker["image"] = image
    docker["image_name"] = image_name
    docker["image_id"] = image_id
    docker["created_at"] = docker_inspect["Created"]
    docker["size"] = docker_inspect["Size"]
    docker["virtual_size"] = docker_inspect["VirtualSize"]

    target.set_attribute("docker", docker)
    target.save()

    logger.info(json.dumps(docker, indent=4))
    return docker


def k8_deploy_v2(item: ItemMixin, target: ItemMixin, stage: str = K8_STAGE_PRODUCTION) -> dict:
    """
    Takes an item that already has a docker and deploys it to our knative cloud.
    Deployment performed by customizing a template service.yaml which is then
    applied to the kubernets cluster via 'kubectl apply'. The command needs to be
    able to find the cluster's credential which need to be installed in the machine
    and be available to the user running the process (the development user or the jobs
    user in production). The call returns immediately, before the cluster has time
    to verify that it can actually be deployed, etc. To see if the service is running
    one can call for status on the k8s service later and obtain an updated status.
    
    Arguments:
        item {ItemMixin} -- An item to be deployed, normally a Model.
        stage {str} -- K8_STAGE_PRODUCTION or K8_STAGE_STAGING
    
    Returns:
        dict -- The knative service information.
    """
    try:
        docker = item.get_attribute("docker")
        if docker is None:
            raise AnaliticoException(f"{item.id} cannot be deployed because its docker has not been built yet.")

        # name of service we are deploying
        name = f"{target.id}-{stage}" if stage != K8_STAGE_PRODUCTION else target.id
        service_name = k8_normalize_name(name)
        service_namespace = "cloud"
        docker_image = docker["image"]

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml") as f:
            service_filename = os.path.join(K8_TEMPLATE_DIR, "service.yaml")
            service_yaml = read_text(service_filename)
            service_yaml = service_yaml.format(
                service_name=service_name,
                service_namespace=service_namespace,
                workspace_id=item.workspace.id if item.workspace else "",
                item_id=item.id,
                docker_image=docker_image,
            )
            save_text(service_yaml, f.name)

            # Deploy service to knative/k8 using kubectl command:
            # kubectl apply --filename briggicloud.yaml -o json
            # https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
            # export KUBECONFIG=$HOME/.kube/config/admin.conf
            cmd_args = ["kubectl", "apply", "--filename", f.name, "-o", "json"]
            service_json, _ = subprocess_run(cmd_args)

            # retrieve existing services
            services = target.get_attribute("service", {})

            # save deployment information inside item, endpoint and job
            attrs = collections.OrderedDict()
            attrs["type"] = "analitico/service"
            attrs["name"] = service_name
            attrs["namespace"] = service_namespace
            attrs["url"] = get_dict_dot(service_json, "status.url", None)
            attrs["docker"] = docker
            attrs["response"] = service_json

            # item's service dictionary can have a 'production' and a 'staging' collection or more
            services[stage] = attrs
            target.set_attribute("service", services)
            target.save()

            logger.info(json.dumps(attrs, indent=4))
            return attrs
    except AnaliticoException as exc:
        raise exc
    except Exception as exc:
        raise AnaliticoException(f"Could not deploy {item.id} because: {exc}") from exc


##
## K8s jobs used to process notebooks
##


def k8_jobs_create(
    item: ItemMixin,
    job_action: str = None,
    job_data: dict = None,
    notification_server_name: str = "https://analitico.ai/",
) -> dict:

    # start from storage config and all all the rest
    configs = k8_get_storage_volume_configuration(item)

    configs["job_action"] = job_action
    configs["job_id"] = job_id = generate_job_id()
    configs["job_id_slug"] = k8_normalize_name(job_id)

    configs["workspace_id"] = item.workspace.id
    configs["workspace_id_slug"] = k8_normalize_name(item.workspace.id)

    configs["item_id"] = item.id
    configs["item_type"] = item.type

    notebook_name = job_data.get("notebook", "notebook.ipynb") if job_data else "notebook.ipynb"
    configs["notebook_name"] = notebook_name

    # the run job needs to run using an image of the code that is the same of what we are running here
    # gitlab tags our build with the environment variable ANALITICO_COMMIT_SHA
    # so we can use that to make sure that the build image is the same
    image_tag = get_image_commit_sha()

    if job_action == analitico.ACTION_RUN or job_action == analitico.ACTION_RUN_AND_BUILD:
        # pass command that should be executed on job docker
        configs["job_template"] = os.path.join(K8_TEMPLATE_DIR, "job-run-template.yaml")
        configs["run_command"] = str(
            ["python3", "./tasks/job.py", os.path.normpath(f"$ANALITICO_DRIVE/{item.type}s/{item.id}/{notebook_name}")]
        )

        configs["run_image"] = f"eu.gcr.io/analitico-api/analitico-client:{image_tag}"

    if job_action == analitico.ACTION_BUILD or job_action == analitico.ACTION_RUN_AND_BUILD:
        # create a model which will host the built recipe which will contain a snapshot
        # of the assets in the recipe at the moment when the model is built. the recipe's
        # notebook is not run when we build, if needed it must be run beforehand.
        assert item.type == analitico.RECIPE_TYPE, "You can only build recipes into models."

        model = Model(workspace=item.workspace)
        model.set_attribute("recipe_id", item.id)
        model.set_attribute("job_id", configs["job_id"])
        model.save()

        # we are not building the recipe INTO a model
        # the image used to run this k8 job will be the standard analitico image with our
        # api package that can access everything. we will run the django manage builder command
        # which is a custom command that will copy the recipe's files into a temporary directory
        # then build and push a docker from it and save the docker's information in the model.
        configs["target_id"] = model.id
        configs["target_type"] = model.type
        configs["job_template"] = os.path.join(K8_TEMPLATE_DIR, "job-build-template.yaml")
        configs["build_command"] = str(
            ["/home/www/analitico/scripts/builder-start.sh", item.id, model.id, notebook_name]
        )

        configs["build_image"] = f"eu.gcr.io/analitico-api/analitico:{image_tag}"

    # webhook notification for job completion
    from api.notifications import get_job_completion_webhook

    notification_url_path = get_job_completion_webhook(item.id, job_id, 10)
    configs["notification_url"] = urllib.parse.urljoin(notification_server_name, notification_url_path)

    if job_action == analitico.ACTION_RUN_AND_BUILD:
        configs["job_template"] = os.path.join(K8_TEMPLATE_DIR, "job-run-and-build-template.yaml")

    if not "job_template" in configs:
        raise AnaliticoException(f"Unknown job action: {job_action}")

    # k8s secret containing the credentials for the workspace mount
    secret_template = os.path.join(K8_TEMPLATE_DIR, "drive-secret-template.yaml")
    secret = k8_customize_and_apply(secret_template, **configs)
    assert secret, "kubectl did not apply the secret"

    # k8s job that will launch
    job = k8_customize_and_apply(configs["job_template"], **configs)
    assert job, "kubctl did not apply the job"
    return job


def k8_jobs_get(item: ItemMixin, job_id: str = None) -> dict:
    try:
        # return specific job filtered by item_id and job_id
        job, _ = subprocess_run(
            cmd_args=["kubectl", "get", "job", k8_normalize_name(job_id), "-n", "cloud", "-o", "json"]
        )
    except Exception as exec:
        raise AnaliticoException(
            f"Job {job_id} cannot be retrieved or not found", status_code=status.HTTP_404_NOT_FOUND
        ) from exec

    # cannot retrieve a job not created for the item
    createdBy = f"analitico.ai/workspace-id" if item.type == "workspace" else f"analitico.ai/item-id"
    if job["metadata"]["labels"][createdBy] != item.id:
        raise AnaliticoException(
            f"Job {job_id} not found for the item {item.id}", status_code=status.HTTP_404_NOT_FOUND
        )

    return job


def k8_jobs_list(item: ItemMixin) -> [dict]:
    # list jobs by workspace or item
    selectBy = f"workspace-id={item.id}" if item.type == "workspace" else f"item-id={item.id}"

    # return list of jobs filtered by item_id
    jobs, _ = subprocess_run(
        cmd_args=[
            "kubectl",
            "get",
            "job",
            "-n",
            "cloud",
            "--selector",
            f"analitico.ai/{selectBy}",
            "--sort-by",
            ".metadata.creationTimestamp",
            "-o",
            "json",
        ]
    )
    return jobs


def k8_job_delete(job_id: str):
    """ Delete the job on Kubernetes """
    try:
        subprocess_run(cmd_args=["kubectl", "delete", "job", job_id, "-n", "cloud"])
    except Exception as exec:
        raise AnaliticoException(
            f"Job {job_id} cannot be deleted or not found", status_code=status.HTTP_404_NOT_FOUND
        ) from exec


##
## Jupyter - allocate and deallocate Jupyter server nodes
##


def k8_jupyter_get(workspace: Workspace, jupyter_name: str = None) -> [dict]:
    """ List of Jupyter StatefulSets created for the workspace """
    if jupyter_name:
        response, _ = kubectl(
            K8_DEFAULT_NAMESPACE,
            "get",
            "statefulSet",
            args=[
                "--selector",
                f"analitico.ai/service=jupyter,analitico.ai/workspace-id={workspace.id},app={jupyter_name}",
            ],
        )
        # kubectl selectors returns an array of items
        items = response.get("items", [])
        if len(items) > 0:
            response = items[0]
        else:
            raise AnaliticoException(f"Resource not found", status_code=status.HTTP_404_NOT_FOUND)
    else:
        response, _ = kubectl(
            K8_DEFAULT_NAMESPACE,
            "get",
            "statefulSet",
            args=["--selector", "analitico.ai/service=jupyter,analitico.ai/workspace-id=" + workspace.id],
        )

    return response


def k8_jupyter_deploy(workspace, jupyter_name: str = None, settings: dict = None):
    """
    Deploy a new Jupyter instance or update the existing one with the given settings.
    If settings are not provided are used those from the workspace or the default one. 
    
    Arguments:
        workspace {Workspace} -- The workspace for which we're allocating Jupyter.
        jupyter_name string -- Name of the Jupyter to update its configuration
        settings {} -- Settings for deploying the Jupyter, like resources
    
    Returns:
        dict -- The jupyter dictionary containing the Kubernetes StatefulSet object
    """
    settings_default = workspace.get_attribute("jupyter")
    if not settings_default:
        # default configuration for Jupyter instances
        settings_default = {
            "settings": {
                "max_instances": 1,
                "replicas": 1,  # start Jupyter when service is deployed
                "enable_scale_to_zero": "true",
                "scale_to_zero_grace_period": "60",
                "requests": {
                    "cpu": "500m",  # number of CPUs
                    "memory": "8Gi",  # memory size
                    "nvidia.com/gpu": 0,  # number of GPUs
                },
                "limits": {"cpu": 4, "memory": "8Gi", "nvidia.com/gpu": 0},
            }
        }
    # resources can be customized by the user but they are
    # considered as resource limit for a Jupyter and the values
    # are limited by those from the billing plan (saved in the workspace)
    settings_default = settings_default["settings"]
    settings = get_dict_dot(settings, "settings", {})

    if jupyter_name:
        # check the given jupyter exists, exception otherwise
        jupyter = k8_jupyter_get(workspace, jupyter_name)
        assert jupyter_name == get_dict_dot(jupyter, "metadata.labels.app")
    else:
        # a workspace can deploy a limited number of Jupyter
        # instances depending on the workspace's billing plan
        total_instances = len(k8_jupyter_get(workspace).get("items", []))
        max_instances = int(settings_default["max_instances"])
        if total_instances >= max_instances:
            raise AnaliticoException(
                f"The maximum number of Jupyter instances has been reached (max {max_instances} / current {total_instances})",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

    cpu_limit = cpu_unit_to_fractional(get_dict_dot(settings_default, "limits.cpu"))
    memory_limit = size_to_bytes(get_dict_dot(settings_default, "limits.memory"))
    gpu_limit = settings_default.get("limits", {}).get("nvidia.com/gpu")
    cpu = cpu_unit_to_fractional(get_dict_dot(settings, "limits.cpu", cpu_limit))
    memory = size_to_bytes(get_dict_dot(settings, "limits.memory", memory_limit))
    gpu = settings.get("limits", {}).get("nvidia.com/gpu", gpu_limit)

    cpu_limit = min(cpu_limit, cpu)
    memory_limit = min(memory_limit, memory)
    gpu_limit = min(gpu_limit, gpu)
    cpu_request = cpu_unit_to_fractional(get_dict_dot(settings_default, "requests.cpu"))
    memory_request = size_to_bytes(get_dict_dot(settings_default, "requests.memory"))
    gpu_request = settings_default.get("requests", {}).get("nvidia.com/gpu")

    # jupyter nomencleture
    # use the given Jupyter name in order to update the settings
    # of the Jupyter with the new specifications. Otherwise a new
    # Jupyter is deployed
    workspace_id_slug = k8_normalize_name(workspace.id)
    jupyter_name = f"jupyter-{workspace_id_slug}-{id_generator()}" if not jupyter_name else jupyter_name
    service_namespace = K8_DEFAULT_NAMESPACE
    controller_name = jupyter_name
    secret_name = f"analitico-{jupyter_name}"

    url = f"https://{jupyter_name}.{service_namespace}.analitico.ai"

    # in case of error the instance must be deployed
    # start from storage config and all the rest
    configs = k8_get_storage_volume_configuration(workspace)

    pod_name = f"{controller_name}-{id_generator(5)}"
    virtualservice_name = f"{jupyter_name}"

    configs["service_name"] = jupyter_name
    configs["service_namespace"] = service_namespace
    configs["workspace_id"] = workspace.id
    configs["workspace_id_slug"] = workspace_id_slug
    configs["controller_name"] = controller_name
    configs["pod_name"] = pod_name
    configs["virtualservice_name"] = virtualservice_name
    configs["service_url"] = url
    configs["jupyter_title"] = get_dict_dot(settings, "title", jupyter_name)
    configs["replicas"] = max(0, min(settings_default["replicas"], settings.get("replicas", 1)))

    # memory limits displayed by nbresuse extension
    configs["jupyter_mem_limit_bytes"] = memory_limit

    # resources
    configs["cpu_request"] = cpu_request
    configs["memory_request"] = memory_request
    configs["gpu_request"] = gpu_request
    configs["cpu_limit"] = cpu_limit
    configs["memory_limit"] = memory_limit
    configs["gpu_limit"] = gpu_limit

    # scale to zero
    enable_scale_to_zero = settings_default.get("enable_scale_to_zero")
    scale_to_zero_grace_period = int(settings_default.get("scale_to_zero_grace_period"))
    configs["enable_scale_to_zero"] = settings.get("enable_scale_to_zero", enable_scale_to_zero)
    configs["scale_to_zero_grace_period"] = min(
        int(settings.get("scale_to_zero_grace_period", scale_to_zero_grace_period)), scale_to_zero_grace_period
    )

    image_tag = get_image_commit_sha()
    configs["image_name"] = f"eu.gcr.io/analitico-api/analitico-client:{image_tag}"

    # generate a jupyter token for login
    token = id_generator(16)

    # k8s secret containing the credentials for the workspace mount
    configs["jupyter_token"] = str(base64.b64encode(token.encode()), "ascii")
    configs["secret_name"] = secret_name

    # k8s secret containing the credentials for the workspace mount
    drive_secret_template = os.path.join(K8_TEMPLATE_DIR, "drive-secret-template.yaml")
    secret = k8_customize_and_apply(drive_secret_template, **configs)

    # jupyter kubernetes service
    jupyter_service_template = os.path.join(K8_TEMPLATE_DIR, "jupyter-service-template.yaml")
    service = k8_customize_and_apply(jupyter_service_template, **configs)

    configs["owner_uid"] = service["metadata"]["uid"]

    # jupyter token
    jupyter_secret_template = os.path.join(K8_TEMPLATE_DIR, "jupyter-secret-template.yaml")
    secret = k8_customize_and_apply(jupyter_secret_template, **configs)

    jupyter_template = os.path.join(K8_TEMPLATE_DIR, "jupyter-template.yaml")
    template = k8_customize_and_apply(jupyter_template, **configs)

    # wait for pod to be started, deployed or restored to one replica
    k8_wait_for_condition(service_namespace, "pod", "condition=Ready", labels=f"app={jupyter_name}", timeout=30)

    jupyter = k8_jupyter_get(workspace, jupyter_name)

    # set the jupyter access token
    annotations = get_dict_dot(jupyter, "metadata.annotations", {})
    annotations["analitico.ai/jupyter-token"] = token
    set_dict_dot(jupyter, "metadata.annotations", annotations)

    return jupyter


def k8_jupyter_kickoff(workspace, jupyter_name: str, settings: dict = None):
    """
    This method checks if the given workspace has been allocated one or more Jupyter servers.
    If the workspace doesn't have a server running or the server has cooled down, it will be
    reallocated.
    
    Arguments:
        workspace {Workspace} -- The workspace for which we're allocating Jupyter.
    
    Returns:
        dict -- The jupyter dictionary containing configurations and servers info.
    """
    if settings:
        # kickoff is performed by the update of the configuration
        jupyter = k8_jupyter_deploy(workspace, jupyter_name=jupyter_name, settings=settings)
    else:
        # update Jupyter with replicas=1
        kubectl(
            K8_DEFAULT_NAMESPACE,
            "scale",
            "statefulSet",
            args=["--replicas=1", "--selector", f"analitico.ai/workspace-id={workspace.id},app={jupyter_name}"],
        )

        # the Jupyter specs returned by the scale operation refers to the
        # component before the operation. Request fresh specs of Jupyter instance.
        jupyter = k8_jupyter_get(workspace, jupyter_name)

        # set the Jupyter access token
        response, _ = kubectl(
            K8_DEFAULT_NAMESPACE,
            "get",
            "secret",
            args=["--selector", f"analitico.ai/workspace-id={workspace.id},app={jupyter_name}"],
        )
        secret = response["items"][0]
        token = base64.b64decode(get_dict_dot(secret, "data.token")).decode("UTF-8")
        annotations = get_dict_dot(jupyter, "metadata.annotations", {})
        annotations["analitico.ai/jupyter-token"] = token
        set_dict_dot(jupyter, "metadata.annotations", annotations)

    return jupyter


def k8_jupyter_deallocate(workspace):
    """ This method is called when a workspace is deleted to deallocate its Jupyter servers (if any). """
    subprocess_run(
        [
            "kubectl",
            "delete",
            "service",
            "--namespace",
            "cloud",
            "--selector",
            f"analitico.ai/service=jupyter,analitico.ai/workspace-id={workspace.id}",
        ]
    )


def k8_scale_to_zero():
    """ Scale to zero services which enabled this feature when they are in idle for a period of time """
    # jupyter statefulset with scale to zero enabled
    statefulsets, _ = kubectl(
        K8_DEFAULT_NAMESPACE, "get", "statefulset", args=["--selector", "analitico.ai/enable-scale-to-zero=true"]
    )

    for statefulset in statefulsets["items"]:
        replicas = statefulset["spec"]["replicas"]
        statefulset_name = statefulset["metadata"]["name"]
        try:
            if replicas > 0:
                desired_replicas = 0
                logger.info("evaluate scale to zero condition for " + statefulset_name)

                app = statefulset["metadata"]["annotations"]["app"]
                workspace_id = statefulset["metadata"]["annotations"]["analitico.ai/workspace-id"]
                grace_period = statefulset["metadata"]["annotations"]["analitico.ai/scale-to-zero-grace-period"]
                namespace = statefulset["metadata"]["namespace"]
                assert app and workspace_id and grace_period

                logger.info(f"{statefulset_name} has scale to zero grace period set to {grace_period} minutes")

                pod, _ = kubectl(
                    namespace, "get", "pod", args=["--selector", f"app={app},analitico.ai/workspace-id={workspace_id}"]
                )
                pod = pod["items"][0]
                pod_name = pod["metadata"]["name"]
                assert pod

                # check creation time to respect the minimum availability
                now = datetime.utcnow()
                # eg: 2019-11-25T11:16:04Z
                running_since = datetime.strptime(pod["metadata"]["creationTimestamp"], "%Y-%m-%dT%H:%M:%SZ")
                running_for = (now - running_since).total_seconds
                logger.info(f"{statefulset_name} has been running since {running_since} ({running_for * 60 } mins)")

                is_enable_to_scale = running_for > (grace_period * 60)

                if not is_enable_to_scale:
                    logger.info(f"skip scaling - pod is running in the grace period")
                else:
                    # check for scaling status against the following metrics
                    metrics = [
                        {
                            "name": "max_http_requests_last_period",
                            "query": f'sum(max_over_time(container_cpu_usage_seconds_total_irate1m{{pod="{pod_name}",container=""}}[{grace_period}m])) by (pod)',
                            # cpu usage in the last period (target millisecs)
                            "target": 100,
                            # in both cases, we cannot make any evaulation without the actual value
                            "replicas_missing_metric": 1,
                            "replicas_status_error": 1,
                        },
                        {
                            "name": "max_http_requests_last_period",
                            "query": f'sum(max_over_time(istio_requests_total_rate1m{{destination_service_name="{app}",container=""}}[{grace_period}m])) by (destination_service_name)',
                            # at least one http request in the grace period
                            "target": 1,
                            # when there are no metrics it might mean that it's not
                            # been made any requests to the service or problems with Prometheus.
                            # In any case we can consider it as zero requests.
                            # The other metrics will compensate this case.
                            "replicas_missing_metric": 0,
                            # we cannot make any evaulation without the actual value
                            "replicas_status_error": 1,
                        },
                    ]

                    desired_replicas = 0
                    for metric in metrics:
                        name = metric["name"]
                        query = metric["query"]
                        target = metric["target"]
                        replicas_missing_metric = metric["replicas_missing_metric"]
                        replicas_status_error = metric["replicas_status_error"]

                        try:
                            # contact Prometheus to retrieve the values for the given query
                            response = requests.get(
                                django.conf.settings.PROMETHEUS_SERVICE_URL + f"/query?query={query}"
                            )
                            if response.status_code != 200:
                                raise AnaliticoException(
                                    f"failed to retrieve metric from Prometheus. Metric: {query}",
                                    status_code=response.status_code,
                                    extra=response.json(),
                                )

                            result = get_dict_dot(response.json(), "data.result")
                            # we expect one point only
                            if len(result) != 1:
                                raise AnaliticoException(
                                    f"invalid metric result. Metric: {query}",
                                    status_code=response.status_code,
                                    extra=result,
                                )
                            value = result.get("value")[1]

                            replicas = 0 if value < target else 1
                        except AnaliticoException as e:
                            # metric returned no value
                            if e.status_code == status.HTTP_200_OK:
                                replicas = 0
                                logger.warning(f"metric {name} is missing. Replicas set to {replicas}")
                            else:
                                # error contacting Prometheus
                                replicas = 1
                                logger.warning(f"metric {name} cannot be evaluated. Replicas set to {replicas}")
                        desired_replicas = max(desired_replicas, replicas)

                    logger.info(f"desired replicas for {statefulset_name} set to {desired_replicas}")
                    if desired_replicas == 0:
                        # do scale to zero
                        kubectl(K8_DEFAULT_NAMESPACE, "scale", f"statefulset/{statefulset_name}", args=["--replicas=0"])
                        logger.info(f"{statefulset_name} is scaled to zero successfully")

        except Exception as exception:
            logger.error(f"cannot perform evaluation of scale to zero for {statefulset_name}. Skip.\n{str(exception)}")


##
## Utilities
##


def k8_customize_and_apply(template_path: str, **kwargs):
    # Deploy a k8 resource using kubectl command:
    # kubectl apply --filename item.yaml -o json
    # https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
    # export KUBECONFIG=$HOME/.kube/config/admin.conf
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml") as f:
        template_yaml = read_text(template_path)
        template_yaml = template_yaml.format(**kwargs)
        save_text(template_yaml, f.name)
        cmd_args = ["kubectl", "apply", "--filename", f.name, "-o", "json"]
        item_json, _ = subprocess_run(cmd_args, None)
        return item_json


def k8_get_storage_volume_configuration(item: ItemMixin) -> dict:
    """ Returns credentials used to mount this item"s workspace storage to K8 jobs or pods. """
    workspace = item if isinstance(item, Workspace) else item.workspace

    storage = workspace.get_attribute("storage")

    assert storage["driver"] == "hetzner-webdav"
    assert storage["url"]
    assert storage["credentials"]["username"]
    assert storage["credentials"]["password"]

    uri = urllib.parse.urlparse(storage["url"])
    username = storage["credentials"]["username"]
    password = storage["credentials"]["password"]

    configs = collections.OrderedDict()
    configs["volume_network_path"] = f"//{uri.netloc}/{username}"
    configs["volume_username"] = base64.b64encode(username.encode("ascii")).decode("ascii")
    configs["volume_password"] = base64.b64encode(password.encode("ascii")).decode("ascii")
    return configs
