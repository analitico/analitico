import collections
import jsonfield
import shutil
import os.path

from django.db import models
from django.utils.crypto import get_random_string

import analitico

from analitico.factory import Factory
from analitico.constants import ACTION_TRAIN
from analitico.status import STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED
from analitico.exceptions import AnaliticoException
from analitico.utilities import read_json

from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace
from .job import Job
from .notebook import nb_run

##
## Model - a trained machine learning model (not model in the sense of Django db model)
##


def generate_model_id():
    return analitico.MODEL_PREFIX + get_random_string()


class Model(ItemMixin, ItemAssetsMixin, models.Model):
    """
    A trained machine learning model which can be used for inferences.
    The "training" attribute of the model includes all the information on
    the training data, parameters, scores and performances. The model can also
    has /data assets like saved CatBoost models, CoreML dumps, etc.
    Trained models are used as immutables in that once created their data
    doesn't change. When you run a new training session you create a new
    model. An endpoint will point to a model to use for predictions. When
    a new model is created, the endpoint is updated to point to the new model.
    """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_model_id)

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

    # Additional attributes are stored as json (used by ItemMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    # A model's notebook describes the recipe used for training and predictions
    notebook = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Jobs
    ##

    def run(self, job: Job, factory: Factory, **kwargs):
        """ Run job actions on the recipe """

        if ACTION_TRAIN not in job.action:
            factory.exception("Model: does not know action: %s", job.action, item=self)

        try:
            # process action runs recipe and creates a trained model
            factory.status(self, STATUS_RUNNING)

            notebook = self.get_notebook()
            if notebook:
                # if dataset has a notebook it will be used to process
                nb_run(notebook_item=self, notebook_name=None, factory=factory, upload=True, job=job)
                try:
                    training_path = os.path.join(factory.get_artifacts_directory(), "training.json")
                    training = read_json(training_path)
                except:
                    factory.warning("Model: could not read training.json")
                    training = {}
            else:
                # if dataset does not have a notebook we will run its plugins
                plugin_settings = self.get_attribute("plugin")
                if not plugin_settings:
                    raise AnaliticoException("Recipe: no notebook or plugins to train with", recipe=self)

                plugin = factory.get_plugin(**plugin_settings)
                training = plugin.run(action=job.action)

                # upload artifacts to model (not to the recipe!)
                # a recipe has a one to many relation with trained models
                factory.upload_artifacts(self)

            self.set_attribute("training", training)
            self.save()

            artifacts = factory.get_artifacts_directory()
            shutil.rmtree(artifacts, ignore_errors=True)

            # job will return information linking to the trained model
            job.set_attribute("recipe_id", self.id)
            job.set_attribute("model_id", self.id)
            job.save()

            factory.status(self, STATUS_COMPLETED)

        except AnaliticoException as e:
            factory.status(self, STATUS_FAILED)
            e.extra["recipe"] = self
            raise e

        except Exception as e:
            factory.status(self, STATUS_FAILED)
            factory.exception("Model: an error occoured while training '%s'", self.id, item=self, exception=e)
