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

    # https://docs.djangoproject.com/en/2.2/topics/auth/customizing/#django.contrib.auth.models.CustomUser.EMAIL_FIELD
    USERNAME_FIELD = "email"

    # https://docs.djangoproject.com/en/2.2/topics/auth/customizing/#django.contrib.auth.models.CustomUser.REQUIRED_FIELDS
    REQUIRED_FIELDS = []

    objects = UserManager()

    # Additional attributes (like profile information) are open ended and are stored as json
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    def save(self, **kwargs):
        """ Force boolean field to have a value to work around some SQL driver bug. """
        if self.is_staff == None:
            self.is_staff = False
        if self.is_superuser == None:
            self.is_superuser = False
        if self.is_active == None:
            self.is_active = False
        super().save(**kwargs)

    def __str__(self):
        return self.email
