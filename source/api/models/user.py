import collections
import jsonfield

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import ugettext_lazy as _

from .usermanager import UserManager
from .items import ItemMixin

USER_THUMBNAIL_SIZE = 120  # thumbnail image size


class User(ItemMixin, AbstractUser):
    """ User model. """

    username = None
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    # Additional attributes (like profile information) are open ended and are stored as json
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    def __str__(self):
        return self.email
