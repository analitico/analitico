import jsonfield
import collections

from django.db import models

import analitico
from analitico.utilities import id_generator

from .items import ItemMixin
from .workspace import Workspace
from .model import Model


def generate_automl_id():
    return analitico.AUTOML_PREFIX + id_generator()


class Automl(ItemMixin, models.Model):
    """ Automl item """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_automl_id)

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
