import analitico.utilities

##
## SettingsMixin
##


class SettingsMixin:
    """
    A simple mixin to implement a class with configurable settings

    When this class or its subclass is initialized it can take any number of named
    arguments in its constructor, eg: obj = SettingsMixing(setting1='value1', setting2='value2')
    You can then access these settings using obj.settings1 or by calling obj.get_setting
    with the name of the setting. The purpose of the mixin is to allow for simple storage,
    retrieval and persistence of settings in classes without having to know a priori their contents.
    This comes useful in the case of plugins for example.
    """

    _settings = {}

    def __init__(self, **kwargs):
        self._settings = kwargs

    def __getattr__(self, setting):
        """ Returns the setting if found or AttributeError if not found """
        if setting in self._settings:
            return self._settings.get(setting)
        raise AttributeError(str(self) + " has no setting: " + setting)

    @property
    def settings(self) -> dict:
        """ Returns reference to settings dictionary """
        return self._settings

    def get_setting(self, setting, default=None):
        """ 
        Returns a setting if configured or the given default value if not.
        You can find the value of hierarchical settings using a dot structure
        like this.that.setting which will navigate the dictionary of settings
        to the correct level.
        """
        return analitico.utilities.get_dict_dot(self._settings, setting, default)
