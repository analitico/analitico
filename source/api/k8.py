import os
import shutil
import tempfile
import datetime
import collections
import json
import urllib
import base64
import string
import collections

import subprocess
from subprocess import PIPE

import django.utils
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

import analitico.utilities

from analitico import AnaliticoException, logger
from analitico.utilities import save_json, save_text, read_text, get_dict_dot, subprocess_run, read_json, copy_directory
from api.factory import factory
from api.models import ItemMixin, Job, Recipe, Model
from api.models.job import generate_job_id
from api.models.notebook import nb_extract_serverless

K8_DEFAULT_NAMESPACE = "cloud"  # service.cloud.analitico.ai
K8_DEFAULT_CONCURRENCY = 20  # concurrent connection per docker

# directory where the template used to dockerize notebooks is stored
K8_TEMPLATE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../serverless/templates/knative"))
assert os.path.isdir(K8_TEMPLATE_DIR)

# directory where the template used to dockerize jobs is stored
K8_JOB_TEMPLATE_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "../../serverless/templates/analitico-job")
)
assert os.path.isdir(K8_JOB_TEMPLATE_DIR)

SOURCE_TEMPLATE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../source"))
assert os.path.isdir(SOURCE_TEMPLATE_DIR)


def k8_normalize_name(name: str):
    return name.lower().replace("_", "-")


def k8_build_v2(item: ItemMixin, target: ItemMixin, job_data: dict = None) -> dict:
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
        copy_directory(K8_TEMPLATE_DIR, tmpdirname)

        # copy current contents of this recipe's files on the attached drive to our docker directory
        item_drive_path = os.environ.get("ANALITICO_DRIVE", None)
        if item_drive_path:
            item_drive_path = os.path.join(item_drive_path, f"{item.type}s/{item.id}")
            copy_directory(item_drive_path, tmpdirname)
        else:
            logger.error(f"k8_build can't find environment variable ANALITICO_DRIVE and cannot copy source item files.")

        # copy analitico SDK and s24 helper methods
        # TODO /analitico and /s24 need to be built into standalone libraries
        copy_directory(os.path.join(SOURCE_TEMPLATE_DIR, "analitico"), os.path.join(tmpdirname, "analitico"))
        copy_directory(os.path.join(SOURCE_TEMPLATE_DIR, "s24"), os.path.join(tmpdirname, "s24"))

        # extract code from notebook
        notebook_name = job_data.get("notebook", "notebook.ipynb") if job_data else "notebook.ipynb"
        notebook_name = os.path.join(tmpdirname, notebook_name)
        notebook = read_json(notebook_name)
        if not notebook:
            raise AnaliticoException(
                f"Item '{item.id}' does not contain a notebook that can be built, please add a notebook."
            )

        # extract source code and scripting from notebook
        source, script = nb_extract_serverless(notebook)
        logger.info(f"scripts:{script}\nsource:\n{source}")

        # overwrite template files
        save_json(notebook, os.path.join(tmpdirname, "notebook.ipynb"), indent=2)
        save_text(source, os.path.join(tmpdirname, "notebook.py"))
        save_text(script, os.path.join(tmpdirname, "notebook.sh"))

        # docker build docker image need to be lowercase
        image_name = f"eu.gcr.io/analitico-api/{item_id_slug}:{target_id_slug}"

        # build docker image, save id temporary file...
        docker_build_args = ["docker", "build", "-t", image_name, tmpdirname]
        subprocess_run(docker_build_args, cwd=tmpdirname)

        # push docker image to registry
        docker_push_args = ["docker", "push", image_name]
        subprocess_run(docker_push_args, timeout=600)  # 10 minutes to upload image

    # retrieve docker information, output is json, parse and add basic info to docker dict
    docker_inspect_args = ["docker", "inspect", image_name]
    docker_inspect, _ = subprocess_run(docker_inspect_args)
    docker_inspect = docker_inspect[0]

    image = docker_inspect["RepoDigests"][0]
    image_id = image[image.find("sha256:") :]

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


# DEPRECATED
def k8_build(item: ItemMixin, job: Job = None, push=True) -> dict:
    """
    Takes an item, extracts its notebook then extracts python code marked for deployment
    from the notebook. Then takes a template directory and applies customizations to it.
    Calls Google Build to build the docker and then publish the docker to a private registry.
    Returns a dictionary with information on the built docker and adds the same dictionary to
    the job as well. Logs operations to the job while they are being performed.
    """
    with tempfile.TemporaryDirectory(prefix="build") as tmpdirname:
        # directory where template files are copied must not exist yet for copytree
        docker_dst = os.path.join(tmpdirname, "docker")

        # copy items from the template used to dockerize
        shutil.copytree(K8_TEMPLATE_DIR, docker_dst)

        # copy analitico SDK and s24 helper methods
        # TODO /analitico and /s24 need to be built into standalone libraries
        shutil.copytree(os.path.join(SOURCE_TEMPLATE_DIR, "analitico"), os.path.join(docker_dst, "analitico"))
        shutil.copytree(os.path.join(SOURCE_TEMPLATE_DIR, "s24"), os.path.join(docker_dst, "s24"))

        # copy artifacts from the model (make actual copies, not symlinks)
        factory.restore_artifacts(item, artifacts_path=docker_dst, symlink=False)

        # extract code from notebook
        notebook_name = job.get_attribute("notebook_name", None) if job else None
        notebook = item.get_notebook(notebook_name=notebook_name)
        if not notebook:
            raise AnaliticoException(
                f"Item '{item.id}' does not contain a notebook that can be built, please add a notebook."
            )

        # extract source code and scripting from notebook
        source, script = nb_extract_serverless(notebook)
        logger.info(f"scripts:{script}\nsource:\n{source}")

        # overwrite template files
        save_json(notebook, os.path.join(docker_dst, "notebook.ipynb"), indent=2)
        save_text(source, os.path.join(docker_dst, "notebook.py"))
        save_text(script, os.path.join(docker_dst, "notebook.sh"))

        # docker build docker image need to be lowercase
        image_name = "eu.gcr.io/analitico-api/" + k8_normalize_name(item.id)

        # build docker image, save id temporary file...
        docker_build_args = ["docker", "build", "-t", image_name, docker_dst]
        subprocess_run(docker_build_args, job, cwd=docker_dst)

        if push:
            # push docker image to registry
            docker_push_args = ["docker", "push", image_name]
            subprocess_run(docker_push_args, job, timeout=600)  # 10 minutes to upload image

    # retrieve docker information, output is json, parse and add basic info to docker dict
    docker_inspect_args = ["docker", "inspect", image_name]
    docker_inspect, _ = subprocess_run(docker_inspect_args, job)
    docker_inspect = docker_inspect[0]

    if push:
        image = docker_inspect["RepoDigests"][0]
        image_id = image[image.find("sha256:") :]
    else:
        image = image_name + ":latest"
        image_id = "latest"

    # save docker information inside item and job
    docker = collections.OrderedDict()
    docker["type"] = "analitico/docker"
    docker["image"] = image
    docker["image_name"] = image_name
    docker["image_id"] = image_id
    docker["created_at"] = docker_inspect["Created"]
    docker["size"] = docker_inspect["Size"]
    docker["virtual_size"] = docker_inspect["VirtualSize"]

    item.set_attribute("docker", docker)
    item.save()
    if job:
        job.set_attribute("docker", docker)
        job.save()

    logger.info(json.dumps(docker, indent=4))
    return docker


def k8_deploy(item: ItemMixin, endpoint: ItemMixin, job: Job = None) -> dict:
    """
    Takes an item that already has a docker and deploys it to our knative cloud.
    Deployment performed by customizing a template service.yaml which is then
    applied to the kubernets cluster via 'kubectl apply'. The command needs to be
    able to find the cluster's credential which need to be installed in the machine
    and be available to the user running the process (the development user or the jobs
    user in production). When the call returns immediately, before the cluster has time
    to verify that it can actually be deployed, etc. To see if the service is running
    one can call for status on the endpoint later and obtain an updated status.
    """
    try:
        docker = item.get_attribute("docker")
        if docker is None:
            raise AnaliticoException(
                f"{item.id} cannot be deployed to {endpoint.id} because its docker has not been built yet."
            )

        # name of service we are deploying
        service_id = job.get_attribute("service_id", endpoint.id) if job else endpoint.id
        service_name = k8_normalize_name(service_id)
        service_namespace = "cloud"
        docker_image = docker["image"]

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml") as f:
            service_filename = os.path.join(K8_TEMPLATE_DIR, "service.yaml")
            service_yaml = read_text(service_filename)
            service_yaml = service_yaml.format(
                service_name=service_name,
                service_namespace=service_namespace,
                item_id=item.id,
                target_id=endpoint.id,
                docker_image=docker_image,
            )
            save_text(service_yaml, f.name)

            # Deploy service to knative/k8 using kubectl command:
            # kubectl apply --filename briggicloud.yaml -o json
            # https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
            # export KUBECONFIG=$HOME/.kube/config/admin.conf
            cmd_args = ["kubectl", "apply", "--filename", f.name, "-o", "json"]
            service_json, _ = subprocess_run(cmd_args, job)

            # save deployment information inside item, endpoint and job
            attrs = collections.OrderedDict()
            attrs["type"] = "analitico/service"
            attrs["name"] = service_name
            attrs["namespace"] = service_namespace
            attrs["url"] = get_dict_dot(service_json, "status.url", None)
            attrs["docker"] = docker
            attrs["response"] = service_json

            item.set_attribute("service", attrs)
            item.save()
            endpoint.set_attribute("service", attrs)
            endpoint.save()

            if job:
                job.set_attribute("service", attrs)
                job.save()

            logger.info(json.dumps(attrs, indent=4))
            return attrs

    except AnaliticoException as exc:
        raise exc

    except Exception as exc:
        raise AnaliticoException(f"Could not deploy {item.id} to {endpoint.id} because: {exc}") from exc


##
## K8s jobs used to process notebooks
##


def k8_jobs_create(item: ItemMixin, job_action: str = None, job_data: dict = None) -> dict:

    # start from storage config and all all the rest
    configs = k8_get_storage_volume_configuration(item)

    configs["job_id"] = job_id = generate_job_id()
    configs["job_id_slug"] = k8_normalize_name(job_id)

    configs["workspace_id"] = item.workspace.id
    configs["workspace_id_slug"] = k8_normalize_name(item.workspace.id)

    configs["item_id"] = item.id
    configs["item_type"] = item.type

    if job_action == analitico.ACTION_RUN or job_action == analitico.ACTION_RUN_AND_BUILD:
        # pass command that should be executed on job docker
        configs["job_template"] = os.path.join(K8_JOB_TEMPLATE_DIR, "job-run-template.yaml")
        configs["run_command"] = str(["python3", "job.py", f"$ANALITICO_DRIVE/{item.type}s/{item.id}/notebook.ipynb"])

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
        configs["job_template"] = os.path.join(K8_JOB_TEMPLATE_DIR, "job-build-template.yaml")
        configs["build_command"] = str(["/home/www/analitico/scripts/builder-start.sh", item.id, model.id])

        # the run job needs to run using an image of the code that is the same of what we are running here
        # gitlab tags our build with the environment variable ANALITICO_COMMIT_SHA
        # so we can use that to make sure that the build image is the same
        # TODO pipeline / we should build site, job, jupyter, baseline dockers with coordinate tag #297
        commit_sha = os.environ.get("ANALITICO_COMMIT_SHA", None)
        if not commit_sha:
            msg = "k8_jobs_create - ANALITICO_COMMIT_SHA is not defined, will build using :latest docker image instead."
            logger.warning(msg)
        build_image_tag = f":{commit_sha}" if commit_sha else ":latest"
        configs["build_image"] = f"eu.gcr.io/analitico-api/analitico-website{build_image_tag}"

    if job_action == analitico.ACTION_RUN_AND_BUILD:
        configs["job_template"] = os.path.join(K8_JOB_TEMPLATE_DIR, "job-run-and-build-template.yaml")

    if not "job_template" in configs:
        raise AnaliticoException(f"Unknown job action: {job_action}")

    # k8s secret containing the credentials for the workspace mount
    secret_template = os.path.join(K8_JOB_TEMPLATE_DIR, "secret-template.yaml")
    secret = k8_customize_and_apply(secret_template, **configs)
    assert secret, "kubectl did not apply the secret"

    # k8s job that will launch
    job = k8_customize_and_apply(configs["job_template"], **configs)
    assert job, "kubctl did not apply the job"
    return job


def k8_jobs_get(item: ItemMixin, job_id: str = None, request: Request = None) -> dict:
    # return specific job filtered by item_id and job_id
    job, _ = subprocess_run(cmd_args=["kubectl", "get", "job", k8_normalize_name(job_id), "-n", "cloud", "-o", "json"])
    assert job["metadata"]["labels"]["analitico.ai/item-id"] == item.id
    return job


def k8_jobs_list(item: ItemMixin, request: Request = None) -> [dict]:
    # return list of jobs filtered by item_id
    jobs, _ = subprocess_run(
        cmd_args=[
            "kubectl",
            "get",
            "job",
            "-n",
            "cloud",
            "--selector",
            f"analitico.ai/item-id={item.id}",
            "--sort-by",
            ".metadata.creationTimestamp",  # TODO newer jobs first
            "-o",
            "json",
        ]
    )
    return jobs


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
    """ Returns credentials used to mount this item's workspace storage to K8 jobs or pods. """
    workspace = item.workspace
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
