import collections
import jsonfield

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string
from rest_framework.exceptions import APIException, NotFound
from rest_framework import status

import analitico.plugin
from analitico.utilities import get_dict_dot, set_dict_dot, logger
from .user import User
from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace
from .job import Job, JobRunner

##
## Endpoint
##

ENDPOINT_PREFIX = "ep_"


def generate_endpoint_id():
    return ENDPOINT_PREFIX + get_random_string()


class Endpoint(ItemMixin, ItemAssetsMixin, models.Model):
    """ An endpoint used to deploy machine learning models """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_endpoint_id)

    # Endpoint is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Description (markdown supported)
    description = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by ItemMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Jobs
    ##

    def run(self, job: Job, runner: JobRunner, **kwargs):
        """ Run job actions on the recipe """
        try:
            # process action runs recipe and creates a trained model
            if job.action == "endpoint/inference":
                plugin_settings = self.get_attribute("plugin")
                if not plugin_settings:
                    # start with basic endpoint pipeline of nothing configured yet
                    plugin_settings = {
                        "type": analitico.plugin.PLUGIN_TYPE,
                        "name": analitico.plugin.ENDPOINT_PIPELINE_PLUGIN,
                    }

                plugin = runner.create_plugin(**plugin_settings)
                results = plugin.run(action=job.action)

                # create a model which will host training results and assets
                model = Model(workspace=self.workspace)
                model.save()

                # upload artifacts to model (not to the recipe!)
                # a recipe has a one to many relation with trained models
                artifacts = runner.get_artifacts_directory()
                runner.upload_artifacts(model)
                shutil.rmtree(artifacts, ignore_errors=True)

                # store training results, link model to recipe and job
                model.set_attribute("recipe_id", self.id)
                model.set_attribute("job_id", job.id)
                model.set_attribute("training", results)
                model.save()

                # job will return information linking to the trained model
                job.set_attribute("recipe_id", self.id)
                job.set_attribute("model_id", model.id)
                job.save()

            self.save()
        except Exception as exc:
            raise exc
