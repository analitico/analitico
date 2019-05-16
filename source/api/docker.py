import os
import shutil
import tempfile
import django.conf

import subprocess
from subprocess import PIPE

from analitico import AnaliticoException
from analitico.utilities import re_match_group, save_json, save_text
from api.factory import Factory
from api.models import ItemMixin, Job
from api.models.notebook import nb_filter_tags, nb_extract_serverless

# directory where the template used to dockerize notebooks is stored
DOCKER_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../serverless/templates/knative")
assert os.path.isdir(DOCKER_TEMPLATE_DIR)

DOCKER_DEFAULT_CONCURRENCY = 20  # concurrent connection per docker
DOCKER_DEFAULT_REGION = "us-central1"  # only region supported by beta


def docker_build(item: ItemMixin, job: Job, factory: Factory) -> dict:
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
        shutil.copytree(DOCKER_TEMPLATE_DIR, docker_dst)

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
        image_name = f"eu.gcr.io/analitico-api/{item.id}"
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
        docker = {
            "image": f"{image_name}@sha256:{image_sha256}",
            "name": image_name,
            "digest": f"sha256:{image_sha256}",
            "size": int(image_size),  # bogus or real?
            "build": {"type": "build/google", "id": build_id, "url": build_url},
        }
        item.set_attribute("docker", docker)
        item.save()
        job.set_attribute("docker", docker)
        job.save()

        return docker


def docker_deploy(item: ItemMixin, endpoint: ItemMixin, job: Job, factory: Factory) -> dict:
    """ Takes an item that has already been built into a Docker and deploys it """
    docker = item.get_attribute("docker")
    if docker is None:
        raise AnaliticoException(
            f"{item.id} cannot be deployed to {endpoint.id} because its docker has not been built yet."
        )

    # service name is the id of the endpoint unless otherwise specified
    service = job.get_attribute("service_id", endpoint.id)
    service = service.lower().replace("_", "-")

    # max concurrent connections per docker
    concurrency = int(job.get_attribute("concurrency", 20))

    # To deploy on Google Cloud Run we use a command like this:
    # https://cloud.google.com/sdk/gcloud/reference/beta/run/deploy
    # gcloud beta run deploy cloudrun02 --image eu.gcr.io/analitico-api/cloudrun02 --set-env-vars=TARGET=Pippo
    cmd_args = [
        "gcloud",
        "beta",
        "run",
        "deploy",
        service,
        "--image",
        docker["image"],
        "--allow-unauthenticated",
        "--concurrency",
        str(concurrency),
        "--region",
        DOCKER_DEFAULT_REGION,
    ]
    cmd_line = " ".join(cmd_args)

    # run build job using google cloud build
    job.append_logs(f"Deploying {item.id} to {endpoint.id} on Google Cloud Run\n{cmd_line}\n\n")
    response = subprocess.run(cmd_args, encoding="utf-8", stdout=PIPE, stderr=PIPE)
    job.append_logs(response.stderr)
    job.append_logs(response.stdout)
    response.check_returncode()

    # Example of response.sterr:
    # Deploying container to Cloud Run service [\x1b[1mep-test-001\x1b[m] in project [\x1b[1manalitico-api\x1b[m] region [\x1b[1mus-central1\x1b[m]\n
    # Deploying new service...\n
    # Setting IAM Policy.........................done\n
    # Creating Revision.......................................................done\n
    # Routing traffic.......................done\n
    # Done.\n

    # This is what it looks like on a Mac:
    # Service [\x1b[1mep-test-001\x1b[m] revision [\x1b[1mep-test-001-00001\x1b[m] has been deployed and is serving traffic at \x1b[1mhttps://ep-test-001-zqsrcwjkta-uc.a.run.app\x1b[m\n
    # This is what it looks like on the server (no bash bold escape sequences like \x1b[1m):
    # Service [ep-test-001] revision [ep-test-001-b65066cc-bd08-4e5e-b4fe-aa86c59280be] has been deployed and is serving traffic at https://ep-test-001-zqsrcwjkta-uc.a.run.app\\n

    logs = response.stderr.replace("\x1b[1m", "")  # remove escape sequences
    revision = re_match_group(r"revision \[([a-z0-9-]*)", logs)
    region = re_match_group(r"region \[([a-z0-9-]*)", logs)
    url = re_match_group(r"is serving traffic at (https:\/\/[a-zA-Z0-9-\.]*)", logs)

    # save deployment information inside item and job
    deploy = {
        "type": "deploy/google-cloud-run",
        "service": service,
        "revision": revision,
        "region": region,
        "url": url,
        "concurrency": concurrency,
    }
    item.set_attribute("deploy", deploy)
    item.save()
    job.set_attribute("deploy", deploy)
    job.save()

    return deploy
