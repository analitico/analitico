import collections
import jsonfield
import pandas as pd
import os
import logging

from django.db import models
from django.utils.crypto import get_random_string

import analitico
import analitico.plugin

from analitico import IFactory
from analitico.constants import ACTION_PREDICT
from analitico.plugin import PluginError
from analitico.utilities import time_ms

from api.factory import ServerFactory
from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace
from .job import Job

##
## Endpoint
##


def generate_endpoint_id():
    return analitico.ENDPOINT_PREFIX + get_random_string()


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

    def run(self, job: Job, factory: IFactory, **kwargs):
        """ Run predictions on the endpoint (with or without a Job) """
        try:
            # bare bones logging to avoid slowing down predictions
            factory.set_logger_level(logging.WARNING)

            # predict action creates a prediction from a trained model
            action = job.action if job else "{}/{}".format(self.type, ACTION_PREDICT)

            model_id = self.get_attribute("model_id")
            if not model_id:
                raise PluginError("Endpoint.run - model_id to be used for prediction is not configured")
            model = factory.get_item(model_id)  # TODO pass request to check auth
            assert model

            # an endpoint tipically will not have its own plugin chain.
            # it will instead use the recipe plugin that were persisted in the
            # model when the recipe was trained. these will tipically include
            # a main RecipePipelinePlugin wrapping a pipeline of data transformation
            # plugins feeding their data into an algorithm which can be trained and
            # later on can generate predictions using its persisted artifacts (the model)

            # in some special cases where the endpoint needs to perform particular tasks
            # that differ from those of the training stage, the endpoint will have its own
            # plugins configured and will run those

            # if the endpoint has its own plugins run them
            plugin_settings = self.get_attribute("plugin")
            if not plugin_settings:
                # if the model has the plugins from the persisted pipeline run those
                plugin_settings = model.get_attribute("plugin")
                if not plugin_settings:
                    # if no persisted pipeline start with basic endpoint pipeline of nothing configured yet
                    plugin_settings = {
                        "type": analitico.plugin.PLUGIN_TYPE,
                        "name": analitico.plugin.ENDPOINT_PIPELINE_PLUGIN,
                    }

            # restore /data artifacts used by plugin to run prediction
            loading_ms = time_ms()
            artifacts_path = factory.get_artifacts_directory()
            for asset in model.get_attribute("data"):
                cache_path = factory.get_cache_asset(model, "data", asset["id"])
                artifact_path = os.path.join(artifacts_path, asset["id"])
                os.symlink(cache_path, artifact_path)
            loading_ms = time_ms(loading_ms)

            # plugin run prediction pipeline and returns predictions as dataframe
            plugin = factory.get_plugin(**plugin_settings)

            # create dataframe from request data
            request = factory.request
            assert request and request.data and request.data["data"]
            data = request.data["data"]
            if isinstance(data, dict):
                data = [data]
            try:
                if self.get_attribute("input", None) == "custom":
                    # pass json input to plugin as is
                    results = plugin.run(data, action=action)
                else:
                    # try converting data into a pandas dataframe
                    df = pd.DataFrame.from_records(data)
                    df_copy = df.copy()
                    results = plugin.run(df, action=action)
            except:
                # TODO log warning or have special marker for endpoints that take data in unusual non tabular formats
                results = plugin.run(data, action=action)
                results["records"] = data

            # additional information
            results["model_id"] = model_id
            results["endpoint_id"] = self.id
            results["performance"]["loading_ms"] = loading_ms

            # track results with async log handler
            factory.set_logger_level(logging.INFO)
            factory.info(action, item=self, prediction=results, model_id=model_id)

            if job:
                job.payload = results
                job.save()

            return results

        except Exception as exc:
            factory.exception(
                "An error occoured while running predictions on %s/%s",
                code="prediction_error",
                item=self,
                model_id=model_id,
            )
