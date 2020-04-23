import os
import requests
import logging
import string
import json

from django.core.management.base import BaseCommand

import docker

from analitico import MODEL_PREFIX, RECIPE_PREFIX

from api import factory
from api.models import Model, Recipe
from api.factory import factory
from api.k8 import k8_build_v2, k8_autodeploy
from analitico.utilities import subprocess_run


def run(cmd: str) -> str:
    print(cmd)
    return subprocess_run(cmd_args=cmd.split(" "))[0]


def run_json(cmd: str) -> dict:
    return run(cmd + " --format=json")


def google_registry_delete_image(image: str):
    delete_cmd = f"gcloud container images delete {image} --force-delete-tags --quiet"
    run(delete_cmd)


def google_registry_delete_image_all_tags(image: str):
    # gcloud container images list-tags eu.gcr.io/analitico-api/rx-078x0yoh
    tags_cmd = f"gcloud container images list-tags {image}"
    tags = run_json(tags_cmd)

    for tag in tags:
        full_image = f"{image}@{tag['digest']}"
        google_registry_delete_image(full_image)


"""
(venv) gionata@Yoshi analitico % gsutil -o GSUtil:default_project_id=analitico-api du -shc
115.45 GiB   gs://data.analitico.ai
1.36 TiB     gs://eu.artifacts.analitico-api.appspot.com
2.88 GiB     gs://public.analitico.ai
65.73 MiB    gs://test.analitico.ai
1.48 TiB     total
"""


class Command(BaseCommand):
    """ 
    A command used to clean used images and their storage from Google Registry 
    https://console.cloud.google.com/gcr/images/analitico-api?project=analitico-api
    """

    def handle(self, *args, **options):

        try:
            # list images currently in the repository
            # https://cloud.google.com/sdk/gcloud/reference/container/images/list
            images_cmd = "gcloud container images list --repository=eu.gcr.io/analitico-api"
            images = run(images_cmd).splitlines()[1:]

            for image in images:
                image_name = image.split("/")[2]
                item_id = image_name.replace("-", "_")

                # remove unused models. images are no longer built specifically for a model.
                # we not build images for each recipe and tag the image with the model id.
                # these models should all be dead and need to be cleaned up in the database
                if item_id.startswith(MODEL_PREFIX):
                    exists = Model.objects.filter(pk=item_id).exists()
                    print(f"{image_name}, exists? {exists}")
                    if not exists:
                        delete_cmd = f"gcloud container images delete {image} --force-delete-tags --quiet"
                        run(delete_cmd)

                # remove images that belong to recipes which no longer exist
                # also remove specific tagged images for models that no longer exists
                if item_id.startswith(RECIPE_PREFIX):
                    recipe_exists = Recipe.objects.filter(pk=item_id).exists()
                    print(f"{image_name}, exists? {recipe_exists}")
                    if not recipe_exists:
                        # recipe no longer exists, remove all its tagged images
                        google_registry_delete_image_all_tags(image)
                    else:
                        # recipe still exists but we can check each of its model tags and see if they can be deleted
                        tags_cmd = f"gcloud container images list-tags {image}"
                        tags = run_json(tags_cmd)
                        for tag in tags:
                            if tag["tags"]:
                                try:
                                    model_tag = tag["tags"][0]
                                    model_id = model_tag.replace("-", "_")
                                    model_exists = Model.objects.filter(pk=model_id).exists()
                                    print(f"{image_name}:{model_tag}, exists? {model_exists}")
                                    if not model_exists:
                                        delete_cmd = f"gcloud container images delete {image}:{model_tag} --force-delete-tags --quiet"
                                        run(delete_cmd)

                                except Exception as exc:
                                    print(exc)

        except Exception as exc:
            print(exc)

        return 0
