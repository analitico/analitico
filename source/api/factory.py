import io
import re
import json
import shutil
import tempfile
import os.path

from django.core.validators import validate_email
from rest_framework.exceptions import NotFound

import analitico
import analitico.plugin
import analitico.utilities

from analitico.factory import Factory

import api.models
import api.plugin

# import plugins for Supermercato24 (if available)
import s24.plugin  # NOQA

# pylint: disable=no-member


##
## ServerFactory
##

# analitico://item_type/item_id/asset_class/asset_id, eg: analitico://dataset/ds_xxx/assets/data.csv
ANALITICO_ASSET_RE = (
    r"analitico:\/\/(?P<item_type>[\a-z]+)s\/(?P<item_id>[\w]+)\/(?P<asset_class>data|assets)\/(?P<asset_id>[-\w\.]+)"
)


class ServerFactory(Factory):
    """ A factory used to run notebooks and plugins in the context of a server with direct access to items via SQL """

    def __init__(self, job=None, mkdtemp=True, **kwargs):
        super().__init__(**kwargs)
        if job:
            self.set_attribute("job", job)
        # special temp directory which is deleted automatically?
        if mkdtemp:
            self._temp_directory = tempfile.mkdtemp(prefix="analitico_temp_")

    ##
    ## Temp and cache directories
    ##

    # Temporary directory which is deleted when factory is disposed
    _temp_directory = None

    def get_temporary_directory(self):
        """ Temporary directory is deleted when ServerFactory is disposed """
        return self._temp_directory if self._temp_directory else super().get_temporary_directory()

    def get_artifacts_directory(self):
        """ Artifacts directory is a subdirectory of temporary and is deleted automatically """
        artifacts_dir = os.path.join(self.get_temporary_directory(), "artifacts")
        if not os.path.isdir(artifacts_dir):
            os.mkdir(artifacts_dir)
        return artifacts_dir

    ##
    ## URL retrieval, authorization and caching
    ##

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
                # format the same way as if it was returned by the server
                asset_json = json.dumps({"data": asset})
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
                    extras = analitico.utilities.read_json(extras_path) if os.path.isfile(extras_path) else {}
                    if fullpath.endswith(".csv") and "rows" not in extras:
                        extras["rows"] = analitico.utilities.get_csv_row_count(fullpath)
                    # upload asset and extras, item will take care of saving to database
                    item.upload_asset_stream(f, "data", path, path_size, None, path, extras)

    def restore_artifacts(self, item):
        """ Restores artifacts stored by item to the artifacts directory """
        assets = item.get_attribute("data")
        if not assets:
            self.warning("ServerFactory.restore_artifacts - item '%s' has not artifacts", item.id, item=item)
            return
        artifacts_path = self.get_artifacts_directory()
        for asset in assets:
            cache_path = self.get_cache_asset(item, "data", asset["id"])
            artifact_path = os.path.join(artifacts_path, asset["id"])
            os.symlink(cache_path, artifact_path)

    ##
    ## Log methods
    ##

    def _prepare_log(self, msg, *args, **kwargs):
        """ Add contextual items to the log record """
        msg, args, kwargs = super()._prepare_log(msg, *args, **kwargs)
        for item_name in ("endpoint", "token", "job", "request"):
            item = self.get_attribute(item_name, None)
            if item:
                kwargs["extra"][item_name] = item
        return msg, args, kwargs

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
            if item_id.startswith(analitico.NOTEBOOK_PREFIX):
                return api.models.Notebook.objects.get(pk=item_id)
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

    ##
    ## with Factory as: lifecycle methods
    ##

    def __exit__(self, exception_type, exception_value, traceback):
        """ Delete any temporary files upon exiting """
        if self._temp_directory:
            shutil.rmtree(self._temp_directory, ignore_errors=True)


# shared instance of server side factory
factory = ServerFactory()
