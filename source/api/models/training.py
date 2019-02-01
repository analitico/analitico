## THIS MODEL IS OBSOLETE AND WILL SOON BE REPLACED BY API.MODEL

import collections
import jsonfield

import analitico.storage

from django.db import models
from django.contrib.auth.models import Group
from rest_framework.exceptions import NotFound, APIException, ParseError, ValidationError

from analitico.utilities import get_dict_dot, logger

from .project import Project


def generate_training_id():
    from django.utils.crypto import get_random_string

    return "trn_" + get_random_string()


class Training(models.Model):
    """ A training session for a machine learning model """

    STATUS_CREATED = "Created"
    STATUS_PROCESSING = "Processing"
    STATUS_COMPLETED = "Completed"
    STATUS_FAILED = "Failed"

    # training id
    id = models.SlugField(primary_key=True, default=generate_training_id)

    # current status, eg: Created, Processing, Completed, Failed
    status = models.SlugField(blank=True, default="Created")

    # model that was trained in this session
    project = models.ForeignKey(Project, on_delete=models.CASCADE, default=None, verbose_name="Project")

    # model settings when training was run
    settings = jsonfield.JSONField(
        load_kwargs={"object_pairs_hook": collections.OrderedDict}, verbose_name="Settings", blank=True, null=True
    )

    # a dictionary with training configuration, results, scores, etc...
    results = jsonfield.JSONField(
        load_kwargs={"object_pairs_hook": collections.OrderedDict}, verbose_name="Results", blank=True, null=True
    )

    # url were test.csv or similar was stored
    # test_url = models.URLField(null=True)

    # url where the data model was stored
    # model_url = models.URLField(null=True)

    # manual notes for this training session
    notes = models.TextField(blank=True, verbose_name="Notes")

    # time when training was run
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    # time when training was updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated")

    def model_url(self):
        return get_dict_dot(self.results, "data.assets.model_url")

    def project_id(self):
        """ Returns project_id of training session """
        return get_dict_dot(self.results, "data.project_id")

    def rmse(self):
        """ Returns root of mean squared error for this training session (if available) """
        return get_dict_dot(self.results, "data.scores.sqrt_mean_squared_error")

    def records(self):
        """ Returns number of records used for training and testing """
        return get_dict_dot(self.results, "data.records.total")

    def is_active(self):
        """ Returns true if this training set is the one that is currently by its model for inferences """
        prj = self.project
        return prj and prj.training_id == self.id

    def activate(self):
        """ Checks if training can be activated and activates it """
        # check if training is ready to go
        logger.info("Training.activate - id: %s, status: %s", self.id, self.status)
        if not self.status == self.STATUS_COMPLETED:
            raise ValidationError(
                detail="Training.status should be "
                + Training.STATUS_COMPLETED
                + " but instead it is "
                + training.status
            )

        # check that model file is really available in storage
        model_url = get_dict_dot(self.results, "data.assets.model_url")
        logger.info("Training.activate - model_url: %s", model_url)
        if not model_url:
            raise NotFound(
                "Training " + self.id + " does not have a trained model file in storage, model_url: " + model_url
            )
        model_filename = analitico.storage.download_file(model_url)
        logger.info("Training.activate - model_filename: %s", model_filename)

        self.project.training_id = self.id
        self.project.save()

    def __str__(self):
        return self.id
