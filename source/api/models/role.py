import collections
import jsonfield

from django.utils.crypto import get_random_string
from django.db import models

from .items import ItemMixin
from .workspace import Workspace
from .user import User

import analitico
import analitico.plugin
import analitico.utilities


def generate_role_id():
    return analitico.ROLE_PREFIX + get_random_string().lower()


class Role(ItemMixin, models.Model):
    """ Role of a specific user on a specific workspace defined via a collection of standard roles and custom permissions. """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_role_id)

    # Role applies to a single workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="roles")

    # Role applies to a single user
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")

    # Comma separated list of standard roles
    roles = models.TextField(blank=True, null=True)

    # Comma separated list of custom permissions
    permissions = models.TextField(blank=True, null=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)
