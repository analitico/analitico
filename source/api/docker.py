
import os
import logging
import shutil
import re

import subprocess
from subprocess import PIPE

from api.factory import Factory


DOCKER_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../serverless/templates/knative")
assert os.path.isdir(DOCKER_TEMPLATE_DIR)



def docker_build(item, factory: Factory) -> dict:

    # copy items from the template used to dockerize
    docker_src = DOCKER_TEMPLATE_DIR
    docker_dst = os.path.join(factory.get_temporary_directory(), "docker")
    shutil.copytree(docker_src, docker_dst)

    # copy artifacts from the model
    factory.restore_artifacts(item, artifacts_path=docker_dst)

    # extract code from notebook
    # TODO

    # gcr.io/analitico-api/knative@sha256:6ca97d37b362dbf6dc12c3ea6b564b905c698785e1eb12fcb80501e5929fec0f

    # update configurations and settings
    # TODO

    # docker build docker image
    # https://developers.google.com/resources/api-libraries/documentation/cloudbuild/v1/python/latest/cloudbuild_v1.projects.builds.html#create
    docker_name = f"gcr.io/analitico-api/{item.id}"
    build_args = [ "gcloud",  "builds", "submit", "--tag", docker_name ]
    
    response = subprocess.run(build_args, cwd=docker_dst, encoding="utf-8", stdout=PIPE, stderr=PIPE)
    response.check_returncode()
    # TODO if throwing return error logs for debugging

    # response.stdout contains a line like this with the image sha256:
    # latest: digest: sha256:4b0effeb10d659ee142530718868003f771c1a7f9e42b8ed2705f3c8934ddf74 size: 3056\nDONE\n
    match = re.search(r"latest: digest: sha256:([0-9a-z]*) size: ([\d]*)", response.stdout)

    # save docker information inside the item
    docker = {
        "image": f"{docker_name}@sha256:{match.group(1)}",
        "size": int(match.group(2)),
        "logs": response.stdout
    }

    item.set_attribute("docker", docker)
    item.save()

    return docker
