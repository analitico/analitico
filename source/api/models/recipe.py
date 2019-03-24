import collections
import jsonfield
import shutil

from django.db import models
from django.utils.crypto import get_random_string

import analitico
import analitico.plugin

from analitico.constants import ACTION_TRAIN
from analitico.status import STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED
from analitico.exceptions import AnaliticoException

from .items import ItemMixin
from .workspace import Workspace
from .job import Job
from .model import Model
from .notebook import nb_run

#
# Recipe - A recipe uses modules and scripts to produce a trained model
#


def generate_recipe_id():
    return analitico.RECIPE_PREFIX + get_random_string()


class Recipe(ItemMixin, models.Model):
    """ A dataset contains a data source description, its metadata and its data """

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

    def run(self, job: Job, factory: analitico.IFactory, **kwargs):
        """ Run job actions on the recipe """
        try:
            # process action runs recipe and creates a trained model
            if ACTION_TRAIN in job.action:
                factory.status(self, STATUS_RUNNING)

                # create a model which will host the recipe pipeline,
                # training results and training artifacts as assets
                model = Model(workspace=self.workspace)
                model.save()
                factory.info("Created model: %s", model.id, item=self)

                notebook = self.get_notebook()
                if notebook:
                    # if dataset has a notebook it will be used to process
                    nb_run(job, factory, notebook_item=self, notebook_name=None, upload_to=model)

                    # TODO training.json
                    training = {}
                else:
                    # if dataset does not have a notebook we will run its plugins
                    plugin_settings = self.get_attribute("plugin")
                    if not plugin_settings:
                        raise AnaliticoException("Recipe: no notebook or plugins to train with", recipe=self)

                    model.set_attribute("plugin", plugin_settings)
                    plugin = factory.get_plugin(**plugin_settings)
                    training = plugin.run(action=job.action)

                    # upload artifacts to model (not to the recipe!)
                    # a recipe has a one to many relation with trained models
                    factory.upload_artifacts(model)

                artifacts = factory.get_artifacts_directory()
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
            factory.status(self, STATUS_COMPLETED)

        except AnaliticoException as e:
            factory.status(self, STATUS_FAILED)
            e.extra["recipe"] = self
            raise e

        except Exception as e:
            factory.status(self, STATUS_FAILED)
            factory.exception("Recipe: an error occoured while training '%s'", self.id, item=self, exception=e)
