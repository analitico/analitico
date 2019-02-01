"""
Job - model for a synch or asynch task like training a model, doing a prediction, etc.
"""

import collections
import jsonfield
import django.utils.crypto

from django.db import models
from .items import ItemMixin
from .workspace import Workspace
from api.factory import ModelsFactory

import analitico
import analitico.plugin


JOB_PREFIX = "jb_"


def generate_job_id():
    """ All Job.id have jb_ prefix followed by a random string """
    return JOB_PREFIX + django.utils.crypto.get_random_string()


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

    # Additional attributes are stored as json (used by AttributesMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Custom fields specific to job
    ##

    # Job.status supports these states
    JOB_STATUS_CREATED = "created"
    JOB_STATUS_PROCESSING = "processing"
    JOB_STATUS_CANCELED = "canceled"
    JOB_STATUS_COMPLETED = "completed"
    JOB_STATUS_FAILED = "failed"

    # Current status, eg: created, processing, completed, failed
    status = models.SlugField(blank=True, default="created")

    # The type of job, or action, for example: workspace/process, model/train, endpoint/inference, etc
    action = models.CharField(blank=True, max_length=64)

    # The item that is the target of this job (eg. model that is trained, dataset that is processed, etc)
    item_id = models.SlugField(blank=True)

    def get_item(self, request=None):
        return ModelsFactory.from_id(self.item_id, request)

    ##
    ## Execution
    ##

    def run(self, request=None):
        try:
            item = self.get_item(request)
            if item:
                item.run(self, request)

            self.status = Job.JOB_STATUS_COMPLETED
            return self
        except Exception as exc:
            raise exc
