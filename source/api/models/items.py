
import collections
import jsonfield

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from analitico.utilities import get_dict_dot, set_dict_dot, logger
from .user import User

WORKSPACE_PREFIX = 'ws_' # workspace with rights and one or more projects and other resources
DATASET_PREFIX   = 'ds_' # dataset source, filters, etc
RECIPE_PREFIX    = 'rx_' # machine learning recipe (an experiment with modules, code, etc) 
MODEL_PREFIX     = 'ml_' # trained machine learning model (not a django model)
SERVICE_PREFIX   = 'ws_' # webservice used to deploy predictive services from models


# Most of these models have similar functionality and attributes so the most logical thing
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
        set_dict_dot(self.attributes, key, value)

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


##
## Workspace - A workspace contains projects, datasets, programs, access rights, etc...
##

def generate_workspace_id():
    return WORKSPACE_PREFIX + get_random_string()

class Workspace(AttributesMixin, models.Model):
    """ A workspace can contain multiple projects, datasets, models, access rights, web services, etc """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_workspace_id, verbose_name=_('Id')) 

    # User that owns the model
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('User'))

    # Group that has access to this model
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Group'))

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True, verbose_name=_('Title'))

    # Description (markdown supported)
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    # Additional attributes are stored as json (used by AttributesMixin)
    attributes = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True, verbose_name=_('Attributes'))


##
## Dataset
##

def generate_dataset_id():
    return DATASET_PREFIX + get_random_string()

class Dataset(AttributesMixin, models.Model):
    """ A dataset contains a data source description, its metadata and its data """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_dataset_id, verbose_name=_('Id')) 

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True, verbose_name=_('Title'))

    # Description (markdown supported)
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    # Additional attributes are stored as json (used by AttributesMixin)
    attributes = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True, verbose_name=_('Attributes'))

    @property
    def columns(self):
        return self.get_attribute('columns')

    @columns.setter
    def columns(self, columns):
        self.set_attribute('columns', columns)


#
# Recipe - A recipe uses modules and scripts to produce a trained model
#

def generate_recipe_id():
    return RECIPE_PREFIX + get_random_string()

class Recipe(AttributesMixin, models.Model):
    """ A dataset contains a data source description, its metadata and its data """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_recipe_id, verbose_name=_('Id')) 

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True, verbose_name=_('Title'))

    # Description (markdown supported)
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    # Additional attributes are stored as json (used by AttributesMixin)
    attributes = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True, verbose_name=_('Attributes'))


##
## Model - a trained machine learning model (not model in the sense of Django db model)
##

def generate_model_id():
    return MODEL_PREFIX + get_random_string()

class Model(AttributesMixin, models.Model):
    """ A trained machine learning model which can be used for inferences """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_model_id, verbose_name=_('Id')) 

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True, verbose_name=_('Title'))

    # Description (markdown supported)
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    # Additional attributes are stored as json (used by AttributesMixin)
    attributes = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True, verbose_name=_('Attributes'))




##
## Service - webservice used to deploy predictive services from models
##

def generate_service_id():
    return SERVICE_PREFIX + get_random_string()

class Service(AttributesMixin, models.Model):
    """ A webservice used to deploy predictive services from models """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_service_id, verbose_name=_('Id')) 

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True, verbose_name=_('Title'))

    # Description (markdown supported)
    description = models.TextField(blank=True, verbose_name=_('Description'))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    # Additional attributes are stored as json (used by AttributesMixin)
    attributes = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True, verbose_name=_('Attributes'))


#
# ItemManager
#

class ItemManager(models.Manager):
    def create_item(self):
        item = self.create()
        return item
