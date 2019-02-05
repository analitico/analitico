import collections

from analitico.utilities import get_dict_dot, set_dict_dot


class AttributeMixin:
    """
    A simple mixin to implement a class with configurable attributes

    When this class or its subclass is initialized it can take any number of named
    arguments in its constructor, eg: obj = AttributesMixing(attribute1='value1', attribute2='value2')
    You can then access these attributes using obj.attribute1 or by calling obj.get_attribute
    with the name of the attribute. The purpose of the mixin is to allow for simple storage,
    retrieval and persistence of attributes in classes without having to know a priori their contents.
    This comes useful in the case of plugins and Django models for example.
    """

    # The attribute field will contain a dictionary. It can be instantiated on demand and can also be
    # implemented as a JSONField in a Django concrete model class to work around a django issue:
    # attributes = jsonfield.JSONField(load_kwargs={'object_pairs_hook': collections.OrderedDict}, blank=True, null=True)
    attributes = None

    def __init__(self, **kwargs):
        self.attributes = kwargs

    def __getattr__(self, key):
        """ Returns the setting if found or AttributeError if not found """
        if self.attributes and key in self.attributes:
            return self.get_attribute(key)
        raise AttributeError(str(self) + " has no attribute: " + key)

    def get_attribute(self, key, default=None):
        """ 
        Returns a setting if configured or the given default value if not.
        You can find the value of hierarchical settings using a dot structure
        like this.that.setting which will navigate the dictionary of settings
        to the correct level.
        """
        if self.attributes:
            return get_dict_dot(self.attributes, key, default)
        return default

    def set_attribute(self, key, value):
        """ Set the value of the given attribute """
        if not self.attributes:
            self.attributes = collections.OrderedDict()
        attributes = self.attributes
        set_dict_dot(attributes, key, value)
        # self.attributes needs to be assigned basically to itself
        # in case the superclass is a Django model which is monitoring
        # the field to decide when a remove SQL instance need to be save()d
        self.attributes = attributes
