import collections
import os.path
import mimetypes

from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from django.db import transaction

from rest_framework import status
from rest_framework.exceptions import APIException, NotFound

import analitico
from analitico import AnaliticoException
from analitico.status import STATUS_CREATED
from analitico.utilities import get_dict_dot, set_dict_dot

import api.storage

# Most of the models have similar functionality and attributes so the most logical thing
# would be to implement an abstract Model and then inherit for all the concrete subclasses.
# However for some reason, probably a django bug, the json field does not work properly in the
# admin interface if it belongs to a superclass. Since the fields are not too many I decided to
# build a mixin for the shared features and just copy the fields manually in each model, not DRY but works.
# The reason for using a json dictionary instead of changing the schema with every new feature
# is that it requires less code and fewer migrations and it lets old and new code coexist on
# the same SQL server without having too many operational headaches. This is similar to a NoSQL approach.

# Interesting read: Modeling Polymorphism in Django With Python
# https://realpython.com/modeling-polymorphism-django-python/


class ItemMixin:

    # Item's unique id (has prefix with item's type, eg: ws_xxx, defined in subclass)
    id = None

    # Workspace that owns this item (or None for workspace itself, defined in subclass)
    workspace = None

    @property
    def type(self):
        """ Returns type of item, eg: workspace, project, dataset, etc """
        return type(self).__name__.lower()

    ##
    ## Attributes
    ##

    # A set of attributes implemented as a JSONField in the concrete class like this to work around a django issue:
    # attributes = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True)
    attributes = None

    def get_attribute(self, key, default=None):
        """ Returns a value from the json data or default if not found (key is in dot notation, eg: this.that) """
        return get_dict_dot(self.attributes, key, default) if self.attributes else default

    def set_attribute(self, key, value):
        if not self.attributes:
            self.attributes = collections.OrderedDict()
        attributes = self.attributes
        set_dict_dot(attributes, key, value)
        self.attributes = attributes  # need to assign or it won't save() it...

    def get_attribute_as_bool(self, key, default: bool = False) -> bool:
        """ Returns attribute as a boolean value. """
        value = self.get_attribute(key, False)
        if isinstance(value, str):
            value = value.lower() == "true" or value == "1"
        return value is True

    ##
    ## Notebooks
    ##

    def get_notebook(self, notebook_name=None):
        """
        Retrieve a Jupyter notebook from the item by name. If the name is None, then
        the default notebook will be retrieved either from a field named "notebook" or
        if the field is not available from the "notebook" key of the model's attributes.
        Same for notebooks with other names.
        """
        if notebook_name is not None and notebook_name != "notebook":
            return self.get_attribute(notebook_name, None)
        return self.notebook

    def set_notebook(self, notebook: dict, notebook_name=None):
        if notebook:
            if "nbformat" not in notebook or "nbformat_minor" not in notebook:
                raise Exception("Notebook should contain 'nbformat' and 'nbformat_minor' fields.")
        if notebook_name is not None and notebook_name != "notebook":
            self.set_attribute(notebook_name, notebook)
        self.notebook = notebook

    ##
    ## Jobs
    ##

    def create_job(self, action, data: dict = None):
        """ Create a job that will be used to perform an action on this item """
        workspace_id = self.workspace.id if self.workspace else self.id
        action = self.type + "/" + action
        job = api.models.Job(item_id=self.id, action=action, workspace_id=workspace_id, status=STATUS_CREATED)

        # job may have had some payload sent
        if data:
            for key, value in data.items():
                job.set_attribute(key, value)

        job.save()
        return job

    ##
    ## Storage and files
    ##

    @property
    def storage(self) -> api.storage.Storage:
        settings = (self.workspace if self.workspace else self).get_attribute("storage")
        return api.storage.Storage.factory(settings) if settings else None

    @property
    def storage_base_path(self) -> str:
        """ Base path for storage files associated with this item. """
        return "/" if self.type == "workspace" else f"/{self.type}s/{self.id}/"

    def download(self, remote_path, local_path_or_fileobj):
        """ Download file from item's storage to local file system. """
        driver = self.storage.driver
        assert driver, f"Storage driver for {self.id} is not configured."
        return driver.download(self.storage_base_path + remote_path, local_path_or_fileobj)

    def __str__(self):
        return self.type + ": " + self.id


##
## ItemsAssetsMixin - methods to handle assets attached to items
##

ASSETS_CLASS_ASSETS = "assets"
ASSETS_CLASS_DATA = "data"


class ItemAssetsMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to upload, update, download and delete
    /assets associated with the model (eg: source data) and /data, for example the
    processed data resulting from an ETL pipeline or machine learning model.
    """

    def _get_asset_path_from_name(self, asset_class, asset_id) -> str:
        """
        Given the asset name (eg: /assets/source.csv or /data/train.csv) this method
        will return the full path of the asset based on the item that owns it, for example
        a dataset with a given id, and the workspace that owns the item. A complete path looks like:
        workspaces/ws_001/datasets/ds_001/assets/dataset-asset.csv
        workspaces/ws_001/assets/workspace-asset.csv
        workspaces/ws_001/datasets/ds_001/data/source.csv
        """
        assert asset_class and asset_id and isinstance(self, ItemMixin)
        if self.workspace:
            w_id = self.workspace.id
            return "workspaces/{}/{}s/{}/{}/{}".format(w_id, self.type, self.id, asset_class, asset_id)
        return "workspaces/{}/{}/{}".format(self.id, asset_class, asset_id)

    def _get_asset_from_id(self, asset_class, asset_id, raise404=False) -> dict:
        """ Returns asset record from a model's array of asset descriptors """
        assert isinstance(self, ItemMixin)
        assets = self.get_attribute(asset_class)
        if assets:
            for asset in assets:
                if asset["id"] == asset_id:
                    return asset
        if raise404:
            detail = "{} does not contain {}/{}".format(self, asset_class, asset_id)
            raise NotFound(detail)
        return None

    def upload_asset_stream(
        self, iterator, asset_class, asset_id, size=0, content_type=None, filename=None, asset_extras=None
    ) -> dict:
        """ Uploads an asset to a model's storage and returns the assets description. """
        assert isinstance(self, ItemMixin)
        asset_parts = os.path.splitext(asset_id)
        asset_id = slugify(asset_parts[0]) + asset_parts[1]
        asset_path = self._get_asset_path_from_name(asset_class, asset_id)
        asset_storage = self.storage
        asset_obj = asset_storage.upload_object_via_stream(iterator, asset_path, extra={"content_type": content_type})

        # we could conceivably have multiple uploads to multiple assets
        # running at the same time. since each of these can be quite long
        # once could complete while the other is still going. therefore the model
        # at this point may be old since some other thread already added an asset.
        # so we lock the model in a transaction, refresh it from database, add the
        # asset and unlock it
        with transaction.atomic():
            # refresh as there may be new assets
            self.refresh_from_db()

            if not content_type:
                content_type, _ = mimetypes.guess_type(asset_id)

            assets = self.get_attribute(asset_class)
            if not assets:
                assets = []

            asset = self._get_asset_from_id(asset_class, asset_id)
            if not asset:
                asset = {"id": asset_id}
                assets.append(asset)

            # if caller provided some extra info it can be saved along with the assets.
            # some keys are reserved and will be overwritten if used (eg. hash)
            if asset_extras:
                for key, value in asset_extras.items():
                    asset[key] = value

            asset["created_at"] = now().isoformat()
            asset["filename"] = filename
            asset["path"] = asset_obj.name
            asset["hash"] = asset_obj.hash
            asset["content_type"] = content_type
            asset["size"] = max(size, asset_obj.size)
            asset["url"] = "analitico://{}s/{}/{}/{}".format(self.type, self.id, asset_class, asset_id)

            # update assets in model and on database
            self.set_attribute(asset_class, assets)
            self.save()
        return asset

    def download_asset_stream(self, asset_class, asset_id):
        """ Returns the asset with the given id along with a stream that can be used to download it from storage. """
        assert isinstance(self, ItemMixin)
        asset = self._get_asset_from_id(asset_class, asset_id, raise404=True)
        asset_storage = self.storage
        storage_obj, storage_stream = asset_storage.download_object_via_stream(asset["path"])

        # update asset with information from storage like etag that can improve browser caching
        if "etag" in storage_obj.extra:
            asset["etag"] = storage_obj.extra["etag"]
        if "last_modified" in storage_obj.extra:
            asset["last_modified"] = storage_obj.extra["last_modified"]
        asset["size"] = storage_obj.size
        asset["hash"] = storage_obj.hash

        return asset, storage_stream

    def _delete_asset(self, asset_class, asset_id) -> dict:
        """ Deletes asset with given asset_id and returns its details. Will raise NotFound if asset_id is invalid. """
        assert asset_class and asset_id and isinstance(self, ItemMixin)
        assets = self.get_attribute(asset_class)
        asset = self._get_asset_from_id(asset_class, asset_id, raise404=True)

        storage = self.storage
        deleted = storage.delete_object(asset["path"])

        if not deleted:
            # TODO if object cannot deleted it may be better to leave orphan in storage and proceed to deleting from assets?
            message = "Cannot delete {}/{} from storage, try again later.".format(asset_class, asset_id)
            analitico.logger.error(message)
            raise APIException(detail=message, code=status.HTTP_503_SERVICE_UNAVAILABLE)

        assets.remove(asset)
        self.set_attribute(asset_class, assets)
        return asset


#
# ItemManager
#


class ItemManager(models.Manager):
    def create_item(self):
        item = self.create()
        return item
