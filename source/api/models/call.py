
import collections
import jsonfield

from django.db import models
from django.contrib.auth.models import Group

from .user import User
from .token import Token

def generate_api_id():
    from django.utils.crypto import get_random_string
    return 'api_' + get_random_string()

class Call(models.Model):
    """ Tracks API calls """

    # random alphanumberical id for this inference
    id = models.SlugField(primary_key=True, default=generate_api_id) 

    # token used for calling
    token = models.ForeignKey(Token, on_delete=models.SET_NULL, verbose_name='Token', blank=True, null=True)

    # url that was called
    url = models.URLField(blank=True)

    HTTP_METHOD_CHOICES = (
        ('GET',     'GET'),
        ('POST',    'POST'),
        ('PUT',     'PUT'),
        ('PATCH',   'PATCH'),
        ('OPTIONS', 'OPTIONS'),
        ('HEAD',    'HEAD')
    )

    # http method used to call (eg: GET, POST, etc)
    method = models.CharField(max_length=16, blank=True, choices=HTTP_METHOD_CHOICES)

    # data sent to request inference
    data = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, verbose_name='Request received', blank=True, null=True)

    # results returned to caller
    results = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, verbose_name='Response sent', blank=True, null=True)

    # status returned to caller
    status = models.IntegerField(default=200)

    # time when inference was requested
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created')

    # last time record updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated')

    class Meta:
        verbose_name = 'call'
        db_table = 'api_call'    
        