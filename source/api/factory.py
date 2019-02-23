from rest_framework.exceptions import NotFound
from django.core.validators import validate_email
import api.models

import analitico
from analitico.utilities import logger


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
from django.db import transaction

import analitico
import analitico.factory
import analitico.plugin
import analitico.utilities

import api.models

import api.plugin

try:
    # import plugins for Supermercato24 (if available)
    import s24.plugin
except:
    pass

# pylint: disable=no-member


##
## ServerFactory
##

# analitico://item_type/item_id/asset_class/asset_id, eg: analitico://dataset/ds_xxx/assets/data.csv
ANALITICO_ASSET_RE = (
    r"analitico:\/\/(?P<item_type>[\a-z]+)s\/(?P<item_id>[\w]+)\/(?P<asset_class>data|assets)\/(?P<asset_id>[-\w\.]+)"
)


class ServerFactory(analitico.factory.Factory):
    """ An IFactory used to run plugins in the context of a server with direct access to items via SQL """

    @property
    def job(self):
        """ Job currently being executed (optional) """
        return self.get_attribute("job")

    # Owner of target item (used for storage, access rights, etc)
    workspace = None

    def __init__(self, job=None, **kwargs):
        super().__init__(**kwargs)
        if job:
            self.set_attribute("job", job)

    ##
    ## Temp and cache directories
    ##

    def get_temporary_directory(self, prefix=None):
        """ If running a job, name temp dir after the job itself """
        return super().get_temporary_directory(self.job.id + "_" if self.job else None)

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
        storage_file = self.get_cache_filename(asset["hash"])

        # if not in cache already download it from storage
        if not os.path.isfile(storage_file):
            storage = item.storage
            assert storage
            _, storage_stream = storage.download_object_via_stream(asset["path"])
            _, storage_file = self.get_cached_stream(storage_stream, asset["hash"])
        return storage_file

    def get_url_stream(self, url, binary=False):
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
            item = self.get_item(item_id)

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
            cache_filename = self.get_cache_asset(item, asset_class, asset_id)
            return open(cache_filename, "rb")
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
                    # if asset has a .info companion read as extra info on the asset
                    extras_path = fullpath + ".info"
                    extras = analitico.utilities.read_json(extras_path) if os.path.isfile(extras_path) else None
                    # upload asset and extras, item will take care of saving to database
                    item.upload_asset_stream(f, "data", path, path_size, None, path, extras)

    ##
    ## Plugin
    ##

    def get_plugin(self, name: str, globals=globals(), **kwargs):
        """ Pass this contect to plugin creator so it can instanciate server plugins too """
        return super().get_plugin(name, globals, **kwargs)

    ##
    ## Factory methods
    ##

    def get_item(self, item_id):
        """ Loads a model from database given its id whose prefix determines the model type, eg: ws_xxx for Workspace. """
        # TODO limit access to objects available with request credentials
        assert isinstance(item_id, str), "Factory.get_item - item_id should be a string with a valid item identifier"
        try:
            if item_id.startswith(analitico.DATASET_PREFIX):
                return api.models.Dataset.objects.get(pk=item_id)
            if item_id.startswith(analitico.ENDPOINT_PREFIX):
                return api.models.Endpoint.objects.get(pk=item_id)
            if item_id.startswith(analitico.JOB_PREFIX):
                return api.models.Job.objects.get(pk=item_id)
            if item_id.startswith(analitico.MODEL_PREFIX):
                return api.models.Model.objects.get(pk=item_id)
            if item_id.startswith(analitico.RECIPE_PREFIX):
                return api.models.Recipe.objects.get(pk=item_id)
            if item_id.startswith(analitico.WORKSPACE_PREFIX):
                return api.models.Workspace.objects.get(pk=item_id)
        except Exception as exc:
            self.warning("get_item: could not find item %s", item_id)
            raise exc
        try:
            validate_email(item_id)
            return api.models.User.objects.get(email=item_id)
        except validate_email.ValidationError:
            pass
        self.warning("get_item: could not find item type for %s", item_id)
        raise NotFound("ServerFactory.get_item - could not find given item type " + item_id)


# shared instance of server side factory
factory = ServerFactory()
