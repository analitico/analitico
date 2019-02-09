import collections
import jsonfield
import pandas as pd
import os

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string
from rest_framework.exceptions import APIException, NotFound
from rest_framework import status

import analitico.plugin
from analitico.plugin import PluginError
from analitico.utilities import get_dict_dot, set_dict_dot, time_ms
from .user import User
from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace
from .job import Job, JobRunner
from api.factory import ModelsFactory

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
    ## Prediction
    ##

    ##
    ## Jobs
    ##

    def run(self, job: Job, runner: JobRunner, **kwargs):
        """ Run job actions on the recipe """
        try:
            # process action runs recipe and creates a trained model
            if job.action == "endpoint/predict":
                plugin_settings = self.get_attribute("plugin")
                if not plugin_settings:
                    # start with basic endpoint pipeline of nothing configured yet
                    plugin_settings = {
                        "type": analitico.plugin.PLUGIN_TYPE,
                        "name": analitico.plugin.ENDPOINT_PIPELINE_PLUGIN,
                    }

                model_id = self.get_attribute("model_id")
                if not model_id:
                    raise PluginError("Endpoint.run - model_id to be used for prediction is not configured")
                model = ModelsFactory.from_id(model_id)  # TODO pass request to check auth
                assert model

                # restore /data artifacts used by plugin to run prediction
                assets_ms = time_ms()
                artifacts_path = runner.get_artifacts_directory()
                for asset in model.get_attribute("data"):
                    cache_path = runner.get_cache_asset(model, "data", asset["id"])
                    artifact_path = os.path.join(artifacts_path, asset["id"])
                    os.symlink(cache_path, artifact_path)
                assets_ms = time_ms(assets_ms)

                # create dataframe from request data
                request = runner.request
                assert request and request.data and request.data["data"]
                data = request.data["data"]
                if isinstance(data, dict):
                    data = [data]
                data_df = pd.DataFrame.from_records(data)

                # plugin run prediction pipeline and returns predictions as dataframe
                plugin = runner.create_plugin(**plugin_settings)
                results = plugin.run(job.action, data_df)

                # additional information
                results["records"] = data
                results["model_id"] = model_id
                results["endpoint_id"] = self.id
                results["performance"]["assets_ms"] = assets_ms

                job.payload = results
                job.save()

            self.save()
        except Exception as exc:
            raise exc
