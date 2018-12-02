
import collections
import jsonfield

from django.db import models
from django.contrib.auth.models import Group

from .project import Project


def generate_training_id():
    from django.utils.crypto import get_random_string
    return 'trn_' + get_random_string()


class Training(models.Model):
    """ A training session for a machine learning model """

    # training id
    id = models.SlugField(primary_key=True, default=generate_training_id) 

    # model that was trained in this session
    project = models.ForeignKey(Project, on_delete=models.CASCADE, default=None, verbose_name='Project')

    # model settings when training was run
    settings = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True)

    # a dictionary with training configuration, results, scores, etc...
    results = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, verbose_name='Results', blank=True, null=True)

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

    def get_test_url(self):
        return None

    def get_model_url(self):
        return None
