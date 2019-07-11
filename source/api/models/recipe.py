import collections
import jsonfield

from django.db import models
from django.utils.crypto import get_random_string

import analitico
import analitico.plugin
import api

from analitico.utilities import id_generator
from .items import ItemMixin
from .workspace import Workspace
from .model import Model, Job


def generate_recipe_id():
    return analitico.RECIPE_PREFIX + id_generator()


class Recipe(ItemMixin, models.Model):
    """ A recipe containing a notebook or a collection of plugins used to train a machine learning model """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_recipe_id)

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Description (markdown supported)
    description = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    # A Jupyter notebook https://nbformat.readthedocs.io/en/latest/
    notebook = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Jobs
    ##

    def create_job(self, action: str, data: dict = None) -> Job:
        """ 
        The recipe does not run training jobs directly, rather it creates a Model
        and then creates a Job that will perform the "train" action on the model (not
        on the recipe). Trained models then become self contained immutables.
        """
        # create a model which will host the recipe pipeline,
        # training results and training artifacts as assets
        model = Model(workspace=self.workspace)
        model.set_attribute("recipe_id", self.id)
        model.set_attribute("plugin", self.get_attribute("plugin"))
        model.set_notebook(self.get_notebook())
        model.save()

        # create and return job that will train the model
        # pylint: disable=no-member
        workspace_id = self.workspace.id if self.workspace else self.id
        action = model.type + "/" + action
        job = api.models.Job(
            item_id=model.id, action=action, workspace_id=workspace_id, status=analitico.status.STATUS_CREATED
        )
        job.set_attribute("recipe_id", self.id)
        job.set_attribute("model_id", model.id)
        job.save()

        # a job is executed asynchronously, potentially on another server
        # and may update the model in the database while we keep holding
        # a reference to a stale and out of date object, so refresh first
        # pylint: disable=no-member
        model = Model.objects.get(pk=model.id)
        model.set_attribute("job_id", job.id)
        model.save()

        return job
