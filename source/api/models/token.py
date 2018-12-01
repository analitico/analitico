
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

import rest_framework.authtoken.models

import binascii
import os

from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.crypto import get_random_string

from .user import User

class Token(models.Model):
    """ Token for bearer token authorization model. """

    # token
    key = models.SlugField(_("Key"), max_length=32, primary_key=True, default=get_random_string)

    # a single user can have zero, one or more tokens
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='User', blank=True)

    # token name can be used to distinguish tokens, eg: mobile, web, server
    name = models.SlugField(blank=True)

    # time when token was created
    created_at = models.DateTimeField(_("Created"), auto_now_add=True)

    class Meta:
        # ensure each user has unique token names
        unique_together = (('user', 'name'),)

    def __str__(self):
        return self.key



