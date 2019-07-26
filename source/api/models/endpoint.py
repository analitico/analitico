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
