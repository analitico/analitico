"""
Job - model for a synch or asynch task like training a model, doing a prediction, etc.
"""

import collections
import jsonfield
import django.utils.crypto
import tempfile
import os.path

from django.db import models
from .items import ItemMixin
from .workspace import Workspace
from api.factory import ModelsFactory

import analitico
import analitico.plugin
import analitico.utilities

JOB_PREFIX = "jb_"


def generate_job_id():
    """ All Job.id have jb_ prefix followed by a random string """
    return JOB_PREFIX + django.utils.crypto.get_random_string()


##
## JobRunner
##


class JobRunner(analitico.plugin.PluginManager):
    """ An IPluginManager used to run plugins in the context of a server Job """

    # Job currently being executed
    job = None

    # Request that originated the job run (optional)
    request = None

    # Target of job being run
    item = None

    # Owner of target item (used for storage, access rights, etc)
    workspace = None

    def __init__(self, job, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
        self.request = request

    def get_temporary_directory(self):
        """ Temporary directory that can be used while a job runs and is deleted afterwards """
        if self._temporary_directory is None:
            self._temporary_directory = tempfile.mkdtemp(prefix=self.job.id + "_")
        return self._temporary_directory

    def run(self):
        """ Runs job then collects artifacts """
        try:
            self.job.status = Job.JOB_STATUS_RUNNING
            self.job.save()

            self.item = self.job.get_item(self.request)
            self.workspace = self.item.workspace if self.item.workspace else self.item

            # item runs the job
            self.item.run(job=self.job, runner=self)

            # upload /data artifacts + metadata created by the item
            if self._temporary_directory:
                directory = self.get_artifacts_directory()
                for path in os.listdir(directory):
                    fullpath = os.path.join(directory, path)
                    # process only files (skip directories and .info files)
                    if os.path.isfile(fullpath) and not path.endswith(".info"):
                        path_size = os.path.getsize(fullpath)
                        with open(fullpath, "rb") as f:
                            asset = self.item._upload_asset_stream(f, "data", path, path_size, None, path)
                            infopath = fullpath + ".info"
                            # if asset has a .info coutn
                            if os.path.isfile(infopath):
                                json = analitico.utilities.read_json(infopath)
                                for key, value in json.items():
                                    asset[key] = value
                                # TODO may need to touch self.item.assets fior it to save properly

            # mark job as completed
            self.item.save()
            self.job.status = Job.JOB_STATUS_COMPLETED
        except Exception as exc:
            self.job.status = Job.JOB_STATUS_FAILED
            raise exc
        finally:
            self.job.save()


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

    # Additional attributes are stored as json (used by AttributesMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Custom fields specific to job
    ##

    # Job.status supports these states
    JOB_STATUS_CREATED = "created"
    JOB_STATUS_RUNNING = "running"
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
        """ Returns the target of this job (eg: dataset to be processed, model to be trained, etc) """
        return ModelsFactory.from_id(self.item_id, request)

    ##
    ## Execution
    ##

    def run(self, request, **kwargs):
        """ Runs the job, collects and uploads artifacts, returns the updated job """
        with JobRunner(self, request, **kwargs) as runner:
            runner.run()
        return self
