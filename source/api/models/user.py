import collections
import jsonfield

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .usermanager import UserManager

class User(AbstractUser):
    """ User model. """

    username = None
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    # Additional attributes (like profile information) are open ended and are stored as json
    attributes = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True, verbose_name=_('Attributes'))
