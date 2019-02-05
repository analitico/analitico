import collections
import jsonfield

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from analitico.utilities import get_dict_dot, set_dict_dot, logger
from .user import User
from .items import ItemMixin
from .workspace import Workspace

#
# Recipe - A recipe uses modules and scripts to produce a trained model
#

RECIPE_PREFIX = "rx_"  # machine learning recipe (an experiment with modules, code, etc)


def generate_recipe_id():
    return RECIPE_PREFIX + get_random_string()


class Recipe(ItemMixin, models.Model):
    """ A dataset contains a data source description, its metadata and its data """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_recipe_id, verbose_name=_("Id"))

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

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
