
import collections
import jsonfield

from django.db import models
from django.contrib.auth.models import Group
from django.utils.crypto import get_random_string

from .user import User

class Model(models.Model):
    """ A machine learning model """

    # id of model, eg: s24-order-time
    id = models.SlugField(max_length=64, primary_key=True) 

    # Owner of this model
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Owner of this model', blank=True, null=True)

    # Group that has access to this model
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, verbose_name='Group that has access to this model', blank=True, null=True)

    # model settings
    settings = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True)

    # training that is currently used for inferences
    # TODO this should be a foreign key but that creates a circular reference...
    training_id = models.SlugField(max_length=6, blank=True) # ForeignKey -> Training
    
    # notes on this machine learning model (markdown format)
    notes = models.TextField(blank=True)

    # model creation date
    created_at = models.DateTimeField(auto_now_add=True)

    # model last updated
    updated_at = models.DateTimeField(auto_now=True)



class Training(models.Model):
    """ A training session for a machine learning model """

    # training id
    id = models.SlugField(max_length=6, primary_key=True, default=get_random_string(length=6)) 

    # model that was trained in this session
    model = models.ForeignKey(Model, on_delete=models.CASCADE, verbose_name='Model that was trained')

    # a dictionary with training configuration, results, etc...
    scores = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, verbose_name='Training scores and information', blank=True, null=True)

    # url were test.csv or similar was stored
    # test_url = models.URLField(null=True)

    # url where the data model was stored
    # model_url = models.URLField(null=True)

    # manual notes for this training session
    notes = models.TextField(blank=True)

    # time when training was run
    created_at = models.DateTimeField(auto_now_add=True)

    # time when training was updated
    updated_at = models.DateTimeField(auto_now=True)



class Inference(models.Model):
    """ Tracks AI models inferences obtained via API calls """

    # random alphanumberical id for this inference
    id = models.SlugField(max_length=6, primary_key=True, default=get_random_string(length=6)) 

    # training that generated this inference
    training = models.ForeignKey(Training, on_delete=models.SET_NULL, blank=True, null=True)

    # user who requested inference
    user = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='User who called the API', blank=True, null=True)

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
