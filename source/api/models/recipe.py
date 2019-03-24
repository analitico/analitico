import collections
import jsonfield
import shutil

from django.db import models
from django.utils.crypto import get_random_string

import analitico
import analitico.plugin

from analitico.constants import ACTION_TRAIN
from analitico.status import STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED
from analitico.exceptions import AnaliticoException

from .items import ItemMixin
from .workspace import Workspace
from .job import Job
from .model import Model
from .notebook import nb_run


def generate_recipe_id():
    return analitico.RECIPE_PREFIX + get_random_string()


class Recipe(ItemMixin, models.Model):
    """ A recipe containing a notebook or a collection of plugins used to train a machine learning model """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_recipe_id)

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Description (markdown supported)
    description = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    # A Jupyter notebook https://nbformat.readthedocs.io/en/latest/
    notebook = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)
