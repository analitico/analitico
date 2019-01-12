
import collections
import datetime
import jsonfield
import os.path

import django.core.files

from django.contrib.auth.models import Group
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

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

class ItemsMixin():

    # Item's unique id (has prefix with item's type, eg: ws_xxx, defined in subclass)
    id = None

    # Workspace that owns this item (or None for workspace itself, defined in subclass)
    workspace = None

    @property
    def type(self):
        """ Returns type of item, eg: workspace, project, dataset, etc """
        return type(self).__name__.lower()

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
        self.attributes = attributes # need to assign or it won't save() it...

    @property
    def notes(self):
        return self.get_attribute('notes')

    @notes.setter
    def notes(self, notes):
        self.set_attribute('notes', notes)

    #@property
    #def settings(self):
    #    return self.get_json('settings')

    ## 
    ## Assets
    ##

    @property
    def storage(self) -> api.storage.Storage:
        settings = (self.workspace if self.workspace else self).get_attribute('storage')
        return api.storage.Storage.factory(settings)


    @property
    def assets(self) -> [dict]:
        assets = self.get_attribute('assets')
        return assets if assets else []


    def _get_asset_from_id(self, asset_id) -> dict:
        for asset in self.assets:
            if asset['id'] == asset_id:
                return asset
        return None


    def _get_asset_path_from_name(self, asset_name=None) -> str:
        if self.workspace:
            return 'workspaces/' + self.workspace.id + '/' + self.type + 's/' + self.id + '/assets/' + asset_name
        return 'workspaces/' + self.id + '/assets/' + asset_name
        

    def upload_asset_via_stream(self, iterator, asset_name, size=0, content_type=None) -> dict:
        """ Uploads an asset to this item's storage and returns the assets description. """

        asset_parts = os.path.splitext(asset_name)
        asset_id = slugify(asset_parts[0]) + asset_parts[1]
        asset_path = self._get_asset_path_from_name(asset_id)
        asset_obj = self.storage.upload_object_via_stream(iterator, asset_path, extra={ 'content_type': content_type })

        assets = self.assets
        if not assets: assets = []

        asset = self._get_asset_from_id(asset_id)
        if not asset: 
            asset = { 'id': asset_id }
            assets.append(asset)

        asset['created_at'] = now().isoformat()
        asset['filename'] = asset_name
        asset['path'] = asset_path
        asset['hash'] = asset_obj.hash
        asset['size'] = max(size,asset_obj.size)
        asset['content_type'] = content_type

        self.set_attribute('assets', assets)
        return asset


    def __str__(self):
        return self.type + ': ' + self.id


#
# ItemManager
#

class ItemManager(models.Manager):
    def create_item(self):
        item = self.create()
        return item
