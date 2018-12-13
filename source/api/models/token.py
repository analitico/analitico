
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

from .user import User

def generate_token_id():
    from django.utils.crypto import get_random_string
    return 'tok_' + get_random_string()


class Token(models.Model):
    """ Token for bearer token authorization model. """

    # token
    key = models.SlugField(_("Key"), max_length=32, primary_key=True, default=generate_token_id)

    # a single user can have zero, one or more tokens
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='User', blank=True, null=True)

    # token name can be used to distinguish tokens, eg: mobile, web, server
    name = models.SlugField(blank=True)

    # time when token was created
    created_at = models.DateTimeField(_("Created"), auto_now_add=True)

    # email address of the owner of this token
    @property
    def email(self):
        return self.user.email
    @email.setter
    def email(self, email):
        self.user = User.objects.get(pk=email)

    def __str__(self):
        return self.key

