import os
import shutil
import tempfile
import django.conf
import collections
import json

import subprocess
from subprocess import PIPE


from analitico import AnaliticoException
from analitico.utilities import re_match_group, save_json, save_text, read_text, read_json, get_dict_dot
from api.factory import Factory
from api.models import ItemMixin, Job
from api.models.notebook import nb_filter_tags, nb_extract_serverless

K8_DEFAULT_NAMESPACE = "cloud"  # service.cloud.analitico.ai
K8_DEFAULT_CONCURRENCY = 20  # concurrent connection per docker
K8_DEFAULT_CLOUDRUN_REGION = "us-central1"  # only region supported by beta

# directory where the template used to dockerize notebooks is stored
K8_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../serverless/templates/knative")
assert os.path.isdir(K8_TEMPLATE_DIR)


def k8_normalize_name(name: str):
    return name.lower().replace("_", "-")


def k8_build(item: ItemMixin, job: Job, factory: Factory) -> dict:
    """
    Takes an item, extracts its notebook then extracts python code marked for deployment
    from the notebook. Then takes a template directory and applies customizations to it.
    Calls Google Build to build the docker and then publish the docker to a private registry.
    Returns a dictionary with information on the built docker and adds the same dictionary to
    the job as well. Logs operations to the job while they are being performed.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        # directory where template files are copied must not exist yet for copytree
        docker_dst = os.path.join(tmpdirname, "docker")

        # copy items from the template used to dockerize
        shutil.copytree(K8_TEMPLATE_DIR, docker_dst)

        # copy artifacts from the model
        factory.restore_artifacts(item, artifacts_path=docker_dst)

        # extract code from notebook
        notebook_name = job.get_attribute("notebook_name", None)
        notebook = item.get_notebook(notebook_name=notebook_name)
        if not notebook:
            raise AnaliticoException(
                f"Item '{item.id}' does not contain a notebook that can be built, please add a notebook."
            )

        # extract source code and scripting from notebook
        source, script = nb_extract_serverless(notebook)

        # overwrite template files
        save_json(notebook, os.path.join(docker_dst, "notebook.ipynb"), indent=2)
        save_text(source, os.path.join(docker_dst, "notebook.py"))
        save_text(script, os.path.join(docker_dst, "notebook.sh"))

        # docker build docker image
        # https://cloud.google.com/sdk/gcloud/reference/builds/submit
        # https://developers.google.com/resources/api-libraries/documentation/cloudbuild/v1/python/latest/cloudbuild_v1.projects.builds.html#create
        # image name needs to be fully lowercase
        image_name = "eu.gcr.io/analitico-api/" + k8_normalize_name(item.id)
        cmd_args = ["gcloud", "builds", "submit", "--tag", image_name]
        cmd_line = " ".join(cmd_args)

        # run build job using google cloud build
        job.append_logs(f"Building Docker\n{cmd_line}\n\n")
        response = subprocess.run(cmd_args, cwd=docker_dst, encoding="utf-8", stdout=PIPE, stderr=PIPE)
        job.append_logs(response.stderr)
        job.append_logs(response.stdout)
        response.check_returncode()

        # extract information on the image from process logs
        # stderr...
        # Logs are available at [https://console.cloud.google.com/gcr/builds/f9bbb62e-ba84-4e91-8d01-e4261454f1fc?project=411722217226]
        # stdout...
        # Successfully built b9bf7caec8c2
        # latest: digest: sha256:068f27226c6cdfd9082142fd93bbd3456c265d8f9719ad767a290c6db9c8be89 size: 3056

        build_id_re = r"Logs are available at \[https://console.cloud.google.com/gcr/builds/([a-z0-9-]*)\?"
        build_id = re_match_group(build_id_re, response.stderr)
        build_url_re = r"Logs are available at \[(https://console.cloud.google.com/gcr/builds/[a-z0-9-]*)\?"
        build_url = re_match_group(build_url_re, response.stderr)

        image_sha256 = re_match_group(r"latest: digest: sha256:([0-9a-z]*) size: ([\d]*)", response.stdout)
        image_size = re_match_group(r"latest: digest: sha256:[0-9a-z]* size: ([\d]*)", response.stdout)

        # save docker information inside item and job
        docker = collections.OrderedDict(
            {
                "image": f"{image_name}@sha256:{image_sha256}",
                "name": image_name,
                "digest": f"sha256:{image_sha256}",
                "size": int(image_size),  # bogus or real?
                "build": {"type": "build/google", "id": build_id, "url": build_url},
            }
        )
        item.set_attribute("docker", docker)
        item.save()
        job.set_attribute("docker", docker)
        job.save()
        return docker


def k8_deploy(item: ItemMixin, endpoint: ItemMixin, job: Job, factory: Factory) -> dict:
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
        service_name = k8_normalize_name(job.get_attribute("service_id", endpoint.id))
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
                docker_image=docker_image
            )
            save_text(service_yaml, f.name)

            # Deploy service to knative/k8 using kubectl command:
            # kubectl apply --filename briggicloud.yaml -o json
            # https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
            # export KUBECONFIG=$HOME/.kube/config/admin.conf
            cmd_args = ["kubectl", "apply", "--filename", f.name, "-o", "json"]
            cmd_line = " ".join(cmd_args)

            job.append_logs(f"Deploying {item.id} to {endpoint.id}\n{cmd_line}\n\n")
            response = subprocess.run(cmd_args, encoding="utf-8", stdout=PIPE, stderr=PIPE, timeout=20)

            if response.returncode:
                job.append_logs(f"kubectl apply failure:\n{response.stderr}\n\n")
                raise AnaliticoException(f"Item {item.id} cannot be deployed to {endpoint.id} because: {response.stderr}")

            job.append_logs(f"kubectl apply success\nresponse:\n\n{response.stdout}\n\n")
            service_json = json.loads(response.stdout)

            # save deployment information inside item, endpoint and job
            attrs = collections.OrderedDict(
                {
                    "type": "analitico/service",
                    "name": service_name,
                    "namespace": service_namespace,
                    "url": get_dict_dot(service_json, "status.url", None),
                    "docker": docker,
                    "response": service_json,
                }
            )
            item.set_attribute("service", attrs)
            item.save()
            endpoint.set_attribute("service", attrs)
            endpoint.save()
            job.set_attribute("service", attrs)
            job.save()
            return attrs

    except AnaliticoException as exc:
        raise exc

    except Exception as exc:
        raise AnaliticoException(f"Could not deploy {item.id} to {endpoint.id} because: {exc}") from exc

def k8_status(item: ItemMixin) -> dict:
    """ Returns the current status of a service that was previously deployed to a kubernets cluster. """
    # kubectl get ksvc ep-test-001-v5 -n cloud -o json
    return {"status": "unknown"}
