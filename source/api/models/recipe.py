import collections
import jsonfield
import os.path
import os
import shutil

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import APIException, NotFound
from rest_framework import status

from analitico.utilities import get_dict_dot, set_dict_dot, logger
from .user import User
from .items import ItemMixin
from .workspace import Workspace
from .job import Job, JobRunner
from .model import Model

#
# Recipe - A recipe uses modules and scripts to produce a trained model
#

RECIPE_PREFIX = "rx_"  # machine learning recipe (an experiment with modules, code, etc)


def generate_recipe_id():
    return RECIPE_PREFIX + get_random_string()


class Recipe(ItemMixin, models.Model):
    """ A dataset contains a data source description, its metadata and its data """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_recipe_id, verbose_name=_("Id"))

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True, verbose_name=_("Title"))

    # Description (markdown supported)
    description = models.TextField(blank=True, verbose_name=_("Description"))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created"))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated"))

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(
        load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True, verbose_name=_("Attributes")
    )

    ##
    ## Jobs
    ##

    def run(self, job: Job, runner: JobRunner, **kwargs):
        """ Run job actions on the recipe """
        try:
            # process action runs recipe and creates a trained model
            if job.action == "recipe/train":
                plugin_settings = self.get_attribute("plugin")
                if not plugin_settings:
                    raise APIException("Recipe.run - the recipe has no configured plugins", status.HTTP_400_BAD_REQUEST)

                plugin = runner.create_plugin(**plugin_settings)
                results = plugin.run(action=job.action)

                model = Model(workspace=self.workspace)
                model.save()

                # upload artifacts to model not to the recipe
                # a recipe has a one to many relation with trained models
                artifacts = runner.get_artifacts_directory()
                runner.upload_artifacts(model)
                shutil.rmtree(artifacts, ignore_errors=True)

                # store training results
                model.set_attribute("recipe_id", self.id)
                model.set_attribute("job_id", job.id)
                model.set_attribute("results", results)
                model.save()

                # job will return information linking to the trained model
                job.set_attribute("recipe_id", self.id)
                job.set_attribute("model_id", model.id)
                job.save()

            self.save()
        except Exception as exc:
            raise exc
