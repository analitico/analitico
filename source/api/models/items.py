
import collections
import jsonfield

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

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

class AttributesMixin():

    # defined in subclass
    id = None

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

    def __str__(self):
        return self.type + ': ' + self.id


#
# ItemManager
#

class ItemManager(models.Manager):
    def create_item(self):
        item = self.create()
        return item
