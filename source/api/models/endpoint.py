import collections
import jsonfield
import pandas as pd
import os
import logging

from django.db import models
from django.utils.crypto import get_random_string

import analitico
import analitico.plugin

from analitico import AnaliticoException
from analitico.factory import Factory
from analitico.constants import ACTION_PREDICT, ACTION_DEPLOY
from analitico.plugin import PluginError
from analitico.utilities import time_ms, read_json, set_dict_dot, id_generator

from api.k8 import k8_build, k8_deploy

from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace
from .job import Job
from .notebook import Notebook, nb_run


##
## Endpoint
##


def generate_endpoint_id():
    return analitico.ENDPOINT_PREFIX + id_generator()


class Endpoint(ItemMixin, ItemAssetsMixin, models.Model):
    """ An endpoint used to deploy machine learning models """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_endpoint_id)

    # Endpoint is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Description (markdown supported)
    description = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by ItemMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Jobs
    ##

    def run(self, job: Job, factory: Factory, **kwargs):
        """ An endpoint can be deployed on kubernetes (will also trigger a docker build if needed) """

        target_id = job.get_attribute("target_id")
        if not target_id:
            raise AnaliticoException("Endpoint.run_deploy - job need to contain the target_id to be deployed")

        # TODO: need to validate that factory.get_item checks permissions on item
        target = factory.get_item(target_id)
        if not target:
            factory.exception("Endpoint: target_id is not configured", item=self)

        # retrieve or build docker, then deploy
        docker = target.get_attribute("docker")
        if not docker:
            docker = k8_build(target, job)

        # deploy docker to cloud
        k8_deploy(target, self, job)
