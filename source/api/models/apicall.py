
import collections
import jsonfield

from django.db import models
from django.contrib.auth.models import Group
from django.utils.crypto import get_random_string

from .user import User
from .token import Token


class ApiCall(models.Model):
    """ Tracks API calls """

    # random alphanumberical id for this inference
    id = models.SlugField(max_length=8, primary_key=True, default=get_random_string(length=8)) 

    # token used for inference
    token = models.SlugField(blank=True) # models.ForeignKey(Token, on_delete=models.SET_NULL, verbose_name='Token used to authorize call', blank=True, null=True)

    # url that was called
    url = models.URLField(blank=True)

    # data sent to request inference
    data = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, verbose_name='Request received', blank=True, null=True)

    # results returned to caller
    results = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, verbose_name='Response sent', blank=True, null=True)

    # status returned to caller
    status = models.IntegerField(default=200)

    # time when inference was requested
    created_at = models.DateTimeField(auto_now_add=True)

    # last time record updated
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'call'
        db_table = 'api_call'    
        