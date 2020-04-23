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
                    exists = Recipe.objects.filter(pk=item_id).exists()
                    print(f"{image_name}, exists? {exists}")
                    if not exists:
                        google_registry_delete_image_all_tags(image)

        except Exception as exc:
            print(exc)

        return 0
