import os
import shutil
import tempfile
import datetime
import collections
import json

import subprocess
from subprocess import PIPE
from rest_framework import status

import analitico.utilities

from analitico import AnaliticoException, logger
from analitico.utilities import save_json, save_text, read_text, get_dict_dot, subprocess_run
from api.factory import factory
from api.models import ItemMixin, Job
from api.models.notebook import nb_extract_serverless

K8_DEFAULT_NAMESPACE = "cloud"  # service.cloud.analitico.ai
K8_DEFAULT_CONCURRENCY = 20  # concurrent connection per docker
K8_DEFAULT_CLOUDRUN_REGION = "us-central1"  # only region supported by beta

# directory where the template used to dockerize notebooks is stored
K8_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../serverless/templates/knative")
assert os.path.isdir(K8_TEMPLATE_DIR)


def k8_normalize_name(name: str):
    return name.lower().replace("_", "-")


def k8_build(item: ItemMixin, job: Job = None) -> dict:
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

        # copy artifacts from the model
        factory.restore_artifacts(item, artifacts_path=docker_dst)

        # extract code from notebook
        notebook_name = job.get_attribute("notebook_name", None) if job else None
        notebook = item.get_notebook(notebook_name=notebook_name)
        if not notebook:
            raise AnaliticoException(
                f"Item '{item.id}' does not contain a notebook that can be built, please add a notebook."
            )

        # extract source code and scripting from notebook
        source, script = nb_extract_serverless(notebook)
        logger.info(f"source:\n{source}\nscripts:{script}")

        # overwrite template files
        save_json(notebook, os.path.join(docker_dst, "notebook.ipynb"), indent=2)
        save_text(source, os.path.join(docker_dst, "notebook.py"))
        save_text(script, os.path.join(docker_dst, "notebook.sh"))

        # docker build docker image need to be lowercase
        image_name = "eu.gcr.io/analitico-api/" + k8_normalize_name(item.id)

        # build docker image, save id temporary file...
        docker_build_args = ["docker", "build", "-t", image_name, docker_dst]
        subprocess_run(docker_build_args, job, cwd=docker_dst)

        # push docker image to registry
        docker_push_args = ["docker", "push", image_name]
        subprocess_run(docker_push_args, job)

    # retrieve docker information, output is json, parse and add basic info to docker dict
    docker_inspect_args = ["docker", "inspect", image_name]
    docker_inspect, _ = subprocess_run(docker_inspect_args, job)
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

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as f:
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
