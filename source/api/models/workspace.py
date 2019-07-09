import collections
import jsonfield
import string

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string

import analitico
from .user import User
from .items import ItemMixin, ItemAssetsMixin

##
## Workspace - A workspace contains projects, datasets, programs, access rights, etc...
##


def generate_workspace_id():
    return analitico.WORKSPACE_PREFIX + analitico.utilities.id_generator()


class Workspace(ItemMixin, ItemAssetsMixin, models.Model):
    """ A workspace can contain multiple projects, datasets, models, access rights, web services, etc """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_workspace_id)

    # User that owns the model
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    # Group that has access to this model
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True, null=True)

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
