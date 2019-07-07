import collections
import jsonfield

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.utils.crypto import get_random_string

import analitico
from analitico import logger

from .user import User

##
## Token
##


def generate_token_id():
    return analitico.TOKEN_PREFIX + get_random_string()


class Token(models.Model):
    """ Token for bearer token authorization model. """

    # token
    id = models.SlugField(max_length=32, primary_key=True, default=generate_token_id)

    # a single user can have zero, one or more tokens
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    # token name can be used to distinguish tokens, eg: mobile, web, server, api
    name = models.SlugField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    # email address of the owner of this token
    @property
    def email(self):
        return self.user.email if self.user else None

    @email.setter
    def email(self, email):
        self.user = User.objects.get(email=email)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return self.id


def get_workspace_token(workspace, create_if_needed=True):
    """ Returns the default authorization token for a specific workspace """
    user = workspace.user
    # pylint: disable=no-member
    token = Token.objects.filter(user=user).first()
    if token is None:
        if not create_if_needed:
            raise analitico.AnaliticoException(
                "Workspace " + workspace.id + " does not have an API token, please create one."
            )
        # create a default token
        token = Token(user=user, id=generate_token_id(), name="api")
        token.save()
    return token.id


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """ Create an API token automatically when a user is created. """
    if created:
        token = Token(user=instance, id=generate_token_id(), name="api")
        token.save()
        logger.debug(f"Created bearer token {token.id} for {instance.email}")
        # https://www.django-rest-framework.org/api-guide/authentication/#generating-tokens
