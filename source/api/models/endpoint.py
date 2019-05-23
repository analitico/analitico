import collections
import jsonfield
import pandas as pd
import os
import logging

from django.db import models
from django.utils.crypto import get_random_string

import analitico
import analitico.plugin

from analitico import AnaliticoException
from analitico.factory import Factory
from analitico.constants import ACTION_PREDICT, ACTION_DEPLOY
from analitico.plugin import PluginError
from analitico.utilities import time_ms, read_json, set_dict_dot

from api.k8 import k8_build, k8_deploy

from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace
from .job import Job
from .notebook import Notebook, nb_run


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

    def run_deploy(self, job: Job, factory: Factory):
        """ Run deploy jobs on the endpoint """
        target_id = job.get_attribute("target_id")
        if not target_id:
            raise AnaliticoException("Endpoint.run_deploy - job need to contain the target_id to be deployed")

        # TODO: need to validate that factory.get_item checks permissions on item
        target = factory.get_item(target_id)
        if not target:
            factory.exception("Endpoint: target_id is not configured", item=self)

        # retrieve or build docker, then deploy
        docker = target.get_attribute("docker")
        if not docker:
            docker = k8_build(target, job)

        # deploy docker to cloud
        k8_deploy(target, self, job)

    def run(self, job: Job, factory: Factory, **kwargs):
        """ Run predictions on the endpoint (with or without a Job) """
        try:
            # predict action creates a prediction from a trained model
            action = job.action if job else "{}/{}".format(self.type, ACTION_PREDICT)

            # deploy action will package model as docker and deploy to serverless
            if action.endswith(ACTION_DEPLOY):
                return self.run_deploy(job, factory)

            # bare bones logging to avoid slowing down predictions
            factory.set_logger_level(logging.WARNING)
            request = factory.request

            model_id = self.get_attribute("model_id")
            if not model_id:
                raise PluginError("Endpoint.run - model_id to be used for prediction is not configured")
            model = factory.get_item(model_id)  # TODO pass request to check auth
            if not model:
                factory.exception("Endpoint: model_id is not configured", item=self)

            # restore /data artifacts stored by model to run prediction
            loading_ms = time_ms()
            factory.restore_artifacts(model)
            loading_ms = time_ms(loading_ms)

            results_path = os.path.join(factory.get_artifacts_directory(), "results.json")
            if os.path.isfile(results_path):
                os.remove(results_path)

            notebook: Notebook = model.get_notebook()
            if notebook:
                # retrieve notebook that was used

                # retrieve data from request
                # TODO could be a file upload like an image, etc
                assert request and request.data
                parameters = request.data

                nb_run(
                    notebook_item=model,
                    parameters=parameters,
                    tags="setup,parameters,prediction",  # run only prediction workflow
                    factory=factory,
                    upload=False,  # do not upload artifacts
                    save=False,  # do not save executed notebook
                    quick=True,  # quicker without outputs
                )

                if not os.path.isfile(results_path):
                    factory.exception(
                        "Endpoint.predict - model ran but didn't save 'results.json' file with predictions"
                    )
                results = read_json(results_path)

            else:
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
                        results = plugin.run(df, action=action)
                except Exception:
                    # TODO log warning or have special marker for endpoints that take data in unusual non tabular formats
                    results = plugin.run(data, action=action)
                    results["records"] = data

            # additional information
            results["model_id"] = model_id
            results["endpoint_id"] = self.id
            set_dict_dot("performance.loading_ms", loading_ms)

            # track results with async log handler
            factory.set_logger_level(logging.INFO)
            factory.info(action, item=self, prediction=results, model_id=model_id)

            if job:
                job.payload = results
                job.save()

            return results

        except Exception:
            factory.exception(
                "An error occoured while running predictions on %s",
                self.id,
                code="prediction_error",
                item=self,
                endpoint_id=self.id,
            )
