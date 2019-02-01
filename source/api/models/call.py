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
from .token import Token

##
## API call
##

API_PREFIX = "api_"


def generate_api_id():
    return API_PREFIX + get_random_string()


class Call(ItemMixin, models.Model):
    """ Tracks API calls """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_api_id)

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Token used for calling
    token = models.ForeignKey(Token, on_delete=models.SET_NULL, blank=True, null=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created"))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated"))

    # Additional attributes are stored as json (used by AttributesMixin)
    attributes = jsonfield.JSONField(
        load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True, verbose_name=_("Attributes")
    )

    ##
    ## Properties (values are stored in attributes field)
    ##

    # URL that was called
    @property
    def url(self):
        return self.get_attribute("url")

    @url.setter
    def url(self, url):
        self.set_attribute("url", url)

    # method = models.CharField(max_length=16, blank=True, choices=HTTP_METHOD_CHOICES)

    # data sent to request inference
    # data = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, verbose_name='Request received', blank=True, null=True)

    # results returned to caller
    # results = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, verbose_name='Response sent', blank=True, null=True)

    # status returned to caller
    # status = models.IntegerField(default=200)

    class Meta:
        verbose_name = "call"
        db_table = "api_call"
