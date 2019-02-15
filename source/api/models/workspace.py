import collections
import jsonfield

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from analitico.utilities import get_dict_dot, set_dict_dot, logger
from .user import User
from .items import ItemMixin, ItemAssetsMixin

##
## Workspace - A workspace contains projects, datasets, programs, access rights, etc...
##

WORKSPACE_TYPE = "workspace"
WORKSPACE_PREFIX = "ws_"  # workspace with rights and one or more projects and other resources


def generate_workspace_id():
    return WORKSPACE_PREFIX + get_random_string()


class Workspace(ItemMixin, ItemAssetsMixin, models.Model):
    """ A workspace can contain multiple projects, datasets, models, access rights, web services, etc """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_workspace_id, verbose_name=_("Id"))

    # User that owns the model
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("User"))

    # Group that has access to this model
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Group"))

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True, verbose_name=_("Title"))

    # Description (markdown supported)
    description = models.TextField(blank=True, verbose_name=_("Description"))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created"))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated"))

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(
        load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True, verbose_name=_("Attributes")
    )
