import collections
import datetime
import jsonfield
import os.path
import mimetypes

import django.core.files

from django.contrib.auth.models import Group
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.crypto import get_random_string
from django.db import transaction

from rest_framework import status
from rest_framework.exceptions import APIException, NotFound

import api.storage

from analitico.utilities import get_dict_dot, set_dict_dot, logger
from .user import User

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

    ## Attributes

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

    ## Basic properties

    @property
    def notes(self):
        return self.get_attribute("notes")

    @notes.setter
    def notes(self, notes):
        self.set_attribute("notes", notes)

    ## Assets

    @property
    def storage(self) -> api.storage.Storage:
        settings = (self.workspace if self.workspace else self).get_attribute("storage")
        return api.storage.Storage.factory(settings)

    @property
    def assets(self) -> [dict]:
        assets = self.get_attribute("assets")
        return assets if assets else []

    def __str__(self):
        return self.type + ": " + self.id


##
## ItemsAssetsMixin - methods to handle assets attached to items
##


class ItemAssetsMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to upload, update, download and delete
    /assets associated with the model (eg: source data) and /data, for example the
    processed data resulting from an ETL pipeline or machine learning model.
    """

    ASSETS_CLASS_ASSETS = "assets"
    ASSETS_CLASS_DATA = "data"

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

    def upload_asset_stream(self, iterator, asset_class, asset_id, size=0, content_type=None, filename=None, asset_extras=None) -> dict:
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

            asset["created_at"] = now().isoformat()
            asset["filename"] = filename
            asset["path"] = asset_obj.name
            asset["hash"] = asset_obj.hash
            asset["content_type"] = content_type
            asset["size"] = max(size, asset_obj.size)
            asset["url"] = "analitico://{}s/{}/{}/{}".format(self.type, self.id, asset_class, asset_id)

            # if caller provided some extra info it can be saved along
            # with the assets info. we need to check that it is not information
            # that will overwrite anything that's already there
            if asset_extras:
                for key, value in asset_extras.items():
                    if key not in asset:
                        asset[key] = value

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
            logger.error(message)
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
