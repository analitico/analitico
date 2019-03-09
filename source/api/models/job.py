import collections
import jsonfield
import django.utils.crypto
import logging

from django.db import models

from .items import ItemMixin
from .workspace import Workspace

import analitico
import analitico.plugin
import analitico.utilities

from analitico.constants import ACTION_TRAIN
from analitico.status import STATUS_RUNNING, STATUS_FAILED, STATUS_COMPLETED
from api.factory import ServerFactory


def generate_job_id():
    """ All Job.id have jb_ prefix followed by a random string """
    return analitico.JOB_PREFIX + django.utils.crypto.get_random_string()


##
## Job
##


class Job(ItemMixin, models.Model):
    """ 
    A job is a model for a piece of work like running an ETL pipeline, training a model,
    doiing a machine learning inference, etc. A job can run synchronously inside a web server
    if it is short (eg inference) or it can be run asynchronously by a worker etc.
    A job is normally completed by running the plugin owned by the requestor of the job.
    """

    ##
    ## Standard fields just like in all other Item models
    ##

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_job_id)

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Description (markdown supported)
    description = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="created")

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name="updated")

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Custom fields specific to job
    ##

    # Current status, eg: created, processing, completed, failed (see analitico.status for values)
    status = models.SlugField(blank=True, default="created")

    # The type of job, or action, for example: workspace/process, model/train, endpoint/inference, etc
    action = models.CharField(blank=True, max_length=64)

    # The item that is the target of this job (eg. model that is trained, dataset that is processed, etc)
    item_id = models.SlugField(blank=True)

    ## Properties

    @property
    def payload(self):
        """ Payload attached to the job (eg: an inference, job results, etc) """
        return self.get_attribute("payload", None)

    @payload.setter
    def payload(self, payload):
        self.set_attribute("payload", payload)

    ##
    ## Execution
    ##

    def run(self, request, **kwargs):
        """ Runs the job, collects and uploads artifacts, returns the updated job """
        with ServerFactory(job=self, request=request, **kwargs) as factory:
            try:
                # log only warnings while predicting to avoid slowing down predictions
                training = ACTION_TRAIN in self.action
                if training:
                    factory.set_logger_level(logging.WARNING)

                self.status = STATUS_RUNNING
                self.save()
                factory.status(self, STATUS_RUNNING)

                # item runs the job
                item = factory.get_item(self.item_id)

                # apply an id to any plugin that may be missing one
                # and save the recipe with the new plugin ids so that
                # the job can track logged actions by each plugin
                plugin = item.get_attribute("plugin")
                if analitico.plugin.apply_plugin_id(plugin):
                    item.set_attribute("plugin", plugin)
                    item.save()

                item.run(job=self, factory=factory)
                item.save()

                self.status = STATUS_COMPLETED
                self.save()
                factory.status(self, STATUS_COMPLETED)

            except Exception as e:
                self.status = STATUS_FAILED
                self.save()
                factory.status(self, STATUS_FAILED)
                factory.exception("An error occoured while running the job: %s", self.id, item=self, exception=e)
