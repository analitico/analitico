import collections
import jsonfield
import shutil

from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import APIException
from rest_framework import status

import analitico
import analitico.plugin

from analitico.utilities import get_dict_dot, set_dict_dot, logger
from .items import ItemMixin
from .workspace import Workspace
from .job import Job
from .model import Model

#
# Recipe - A recipe uses modules and scripts to produce a trained model
#


def generate_recipe_id():
    return analitico.RECIPE_PREFIX + get_random_string()


class Recipe(ItemMixin, models.Model):
    """ A dataset contains a data source description, its metadata and its data """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_recipe_id, verbose_name=_("Id"))

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

    ##
    ## Jobs
    ##

    def run(self, job: Job, factory: analitico.IFactory, **kwargs):
        """ Run job actions on the recipe """
        try:
            # process action runs recipe and creates a trained model
            if job.action == "recipe/train":
                plugin_settings = self.get_attribute("plugin")
                if not plugin_settings:
                    raise APIException("Recipe.run - the recipe has no configured plugins", status.HTTP_400_BAD_REQUEST)

                # apply an id to any plugin that may be missing one
                # and save the recipe with the new plugin ids so that
                # the job can track logged actions by each plugin
                if analitico.plugin.apply_plugin_id(plugin_settings):
                    self.set_attribute("plugin", plugin_settings)
                    self.save()

                plugin = factory.get_plugin(**plugin_settings)
                training = plugin.run(action=job.action)

                # create a model which will host the recipe pipeline,
                # training results and training artifacts as assets
                model = Model(workspace=self.workspace)
                model.set_attribute("plugin", plugin_settings)
                model.save()

                # upload artifacts to model (not to the recipe!)
                # a recipe has a one to many relation with trained models
                artifacts = factory.get_artifacts_directory()
                factory.upload_artifacts(model)
                shutil.rmtree(artifacts, ignore_errors=True)

                # store training results, link model to recipe and job
                model.set_attribute("recipe_id", self.id)
                model.set_attribute("job_id", job.id)
                model.set_attribute("training", training)
                model.save()

                # job will return information linking to the trained model
                job.set_attribute("recipe_id", self.id)
                job.set_attribute("model_id", model.id)
                job.save()

            self.save()
        except Exception as exc:
            raise exc
