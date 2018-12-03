
import collections
import jsonfield

from django.db import models
from django.contrib.auth.models import Group
from django.utils.crypto import get_random_string

from .user import User

class Project(models.Model):
    """ A machine learning project """

    # id of model, eg: s24-order-time
    id = models.SlugField(max_length=64, primary_key=True) 

    # Owner of this model
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Owner of this project', blank=True, null=True)

    # Group that has access to this model
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, verbose_name='Group that has access to this project', blank=True, null=True)

    # model settings
    settings = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True)

    # training that is currently used for inferences
    # TODO this should be a foreign key but that creates a circular reference...
    training_id = models.SlugField(blank=True) # ForeignKey -> Training
    
    # notes on this machine learning model (markdown format)
    notes = models.TextField(blank=True)

    # model creation date
    created_at = models.DateTimeField(auto_now_add=True)

    # model last updated
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.id 
