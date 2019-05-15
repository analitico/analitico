import os
import shutil
import tempfile

import subprocess
from subprocess import PIPE

from analitico.utilities import re_match_group
from api.factory import Factory
from api.models import ItemMixin, Job

# directory where the template used to dockerize notebooks is stored
DOCKER_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../serverless/templates/knative")
assert os.path.isdir(DOCKER_TEMPLATE_DIR)


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
        # TODO

        # gcr.io/analitico-api/knative@sha256:6ca97d37b362dbf6dc12c3ea6b564b905c698785e1eb12fcb80501e5929fec0f

        # update configurations and settings
        # TODO

        # docker build docker image
        # https://cloud.google.com/sdk/gcloud/reference/builds/submit
        # https://developers.google.com/resources/api-libraries/documentation/cloudbuild/v1/python/latest/cloudbuild_v1.projects.builds.html#create
        image_name = f"eu.gcr.io/analitico-api/{item.id}"
        build_args = ["gcloud", "builds", "submit", "--tag", image_name]

        # run build job using google cloud build
        job.append_logs("Building Docker\n" + " ".join(build_args) + "\n")
        response = subprocess.run(build_args, cwd=docker_dst, encoding="utf-8", stdout=PIPE, stderr=PIPE)
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

        # save docker information inside item
        docker = {
            "image": f"{image_name}@sha256:{image_sha256}",
            "name": image_name,
            "digest": f"sha256:{image_sha256}",
            "size": int(image_size),  # bogus or real?
            "build": {"type": "google/build", "id": build_id, "url": build_url},
        }
        item.set_attribute("docker", docker)
        item.save()

        return docker
