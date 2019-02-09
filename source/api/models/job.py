"""
Job - model for a synch or asynch task like training a model, doing a prediction, etc.
"""

import collections
import jsonfield
import django.utils.crypto
import tempfile
import os.path
import io
import re
import json
import io

from django.db import models
from .items import ItemMixin
from .workspace import Workspace
from api.factory import ModelsFactory

import analitico
import analitico.manager
import analitico.plugin
import analitico.utilities
import api.plugin

JOB_PREFIX = "jb_"


def generate_job_id():
    """ All Job.id have jb_ prefix followed by a random string """
    return JOB_PREFIX + django.utils.crypto.get_random_string()


##
## JobRunner
##

# analitico://item_type/item_id/asset_class/asset_id, eg: analitico://dataset/ds_xxx/assets/data.csv
ANALITICO_ASSET_RE = (
    r"analitico:\/\/(?P<item_type>[\a-z]+)s\/(?P<item_id>[\w]+)\/(?P<asset_class>data|assets)\/(?P<asset_id>[-\w\.]+)"
)


class JobRunner(analitico.manager.PluginManager):
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

    def create_plugin(self, name: str, **kwargs):
        """
        Create a plugin given its name and the environment it will run in.
        Any additional parameters passed to this method will be passed to the
        plugin initialization code and will be stored as a plugin setting.
        """
        klass = self._get_class_from_fully_qualified_name(name, globals=globals())
        if not klass:
            raise analitico.plugin.PluginError("JobRunner - can't find plugin: " + name)
        return (klass)(manager=self, **kwargs)

    def get_temporary_directory(self):
        """ Temporary directory that can be used while a job runs and is deleted afterwards """
        if self._temporary_directory is None:
            self._temporary_directory = tempfile.mkdtemp(prefix=self.job.id + "_")
        return self._temporary_directory

    def get_cache_asset(self, item, asset_class, asset_id):
        """ 
        Returns filename of cached asset after downloading it if necessary. 
        File should be used as read only and copied if it needs to be modified.
        """
        asset = item._get_asset_from_id(asset_class, asset_id, raise404=True)
        assert asset
        # name of the file in cache is determined by its hash so all files are unique and
        # we do not need to check versions, eg. if we have it with the correct name it's
        # the correct version and we can save a rountrip to check with the server
        storage_file = os.path.join(self.get_cache_directory(), "cache_" + asset["hash"])

        # if not in cache already download it from storage
        if not os.path.isfile(storage_file):
            storage = item.storage
            assert storage
            storage_path = asset["path"]
            storage_obj, storage_stream = storage.download_object_via_stream(storage_path)
            storage_temp_file = storage_file + ".tmp_" + django.utils.crypto.get_random_string()
            with open(storage_temp_file, "wb") as f:
                for b in storage_stream:
                    f.write(b)
            os.rename(storage_temp_file, storage_file)
        return storage_file

    def get_url_stream(self, url):
        """ Job runner retrieves assets directly from cloud storage while using super for regular URLs """
        # temporarily while all internal urls are updated prepend analitico://
        if url.startswith("workspaces/ws_"):
            url = "analitico://" + url

        # job runner reads assets straight from cloud storage
        match = re.search(ANALITICO_ASSET_RE, url)
        if match:
            # find asset indicated in the url
            item_id = match.group("item_id")
            asset_class = match.group("asset_class")
            asset_id = match.group("asset_id")

            # TODO should check that current requestor has access rights to this item
            item = ModelsFactory.from_id(item_id)

            # replace shorthand /data/csv with /data/data.csv
            wants_json = False
            if asset_class == "data":
                if asset_id == "csv":
                    asset_id = "data.csv"
                if asset_id == "info":
                    asset_id = "data.csv"
                    wants_json = True

            asset = item._get_asset_from_id(asset_class, asset_id, raise404=True)
            if wants_json:
                asset_json = json.dumps(asset)
                return io.StringIO(asset_json)

            storage = item.storage
            if not storage:
                raise analitico.plugin.PluginError(
                    "JobRunner.get_url_stream - storage is not configured correctly for item: " + self.item.id
                )
            storage_path = asset["path"]
            storage_obj, storage_stream = storage.download_object_via_stream(storage_path)

            # download stream to a cache file then hand over stream to file
            # the temporary file is named after the hash of the file contents in storage.
            # if we already have a file in cache with the same name, we can be assured that
            # its contents are the same as the requested file and we can serve directly from file.
            storage_file = os.path.join(self.get_cache_directory(), "cache_" + storage_obj.hash)
            if not os.path.isfile(storage_file):
                storage_temp_file = storage_file + ".tmp_" + django.utils.crypto.get_random_string()
                with open(storage_temp_file, "wb") as f:
                    for b in storage_stream:
                        f.write(b)
                os.rename(storage_temp_file, storage_file)
            return open(storage_file, "rb")

        # base class handles regular URLs
        return super().get_url_stream(url)

    def upload_artifacts(self, item):
        """ Uploads all files in the artifacts directory to the given item's data assets """
        directory = self.get_artifacts_directory()
        for path in os.listdir(directory):
            fullpath = os.path.join(directory, path)
            # process only files (skip directories and .info files)
            if os.path.isfile(fullpath) and not path.endswith(".info"):
                path_size = os.path.getsize(fullpath)
                with open(fullpath, "rb") as f:
                    asset = item._upload_asset_stream(f, "data", path, path_size, None, path)
                    infopath = fullpath + ".info"
                    # if asset has a .info companion
                    if os.path.isfile(infopath):
                        json = analitico.utilities.read_json(infopath)
                        for key, value in json.items():
                            asset[key] = value
        # TODO may need to touch self.item.assets for it to save properly
        item.save()

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
            self.upload_artifacts(self.item)

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

    # Additional attributes are stored as json (used by AttributeMixin)
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
        with JobRunner(self, request, **kwargs) as runner:
            runner.run()
        return self
