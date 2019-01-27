import logging
import pandas
from abc import ABC, abstractmethod

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
        return self._settings.get(setting, None)

    @property
    def settings(self):
        return self._settings

    def get_setting(self, setting, default=None):
        """ Returns a setting if configured or the given default value """
        return self._settings.get(setting, default)


##
## PluginEnvironment
##


class IPluginEnvironment(ABC, SettingsMixin):
    """ A base abstract class for settings related to the plugins' runtime environment """

    pass


class PluginEnvironment(IPluginEnvironment):
    """ A plugin environment (concrete class) """

    pass


##
## IPlugin - base class for all plugins
##


class IPlugin(ABC, SettingsMixin):
    """ Abstract base class for Analitico plugins """

    class Meta:
        """ Plugin metadata is exposed in its inner class """

        name = None

    # Environment that the plugin is running in
    env = None

    @property
    def name(self):
        return type(self).__name__

    @property
    def logger(self):
        """ Logger that can be used by the plugin to communicate errors, etc with host """
        return logging.getLogger(self.name)

    def __init__(self, env: IPluginEnvironment = None, **kwargs):
        super().__init__(**kwargs)
        self.env = env

    def activate(self, **kwargs):
        """ Called when the plugin is initially activated """
        pass

    @abstractmethod
    def process(self, **kwargs):
        """ Run will do in the subclass whatever the plugin does """
        pass

    def deactivate(self, **kwargs):
        """ Called before the plugin is deactivated and finalized """
        pass

    def __str__(self):
        return self.name


##
## IDataframeSourcePlugin - base class for plugins that create dataframes
##


class IDataframeSourcePlugin(IPlugin):
    """ A plugin that creates a pandas dataframe from a source (eg: csv file, sql query, etc) """

    class Meta(IPlugin.Meta):
        inputs = None
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    @abstractmethod
    def process(self, **kwargs):
        """ Run creates a dataset from the source and returns it """
        pass


##
## IDataframePlugin - base class for plugins that manipulate pandas dataframes
##


class IDataframePlugin(IPlugin):
    """
    A plugin that takes a pandas dataframe as input,
    manipulates it and returns a pandas dataframe
    """

    class Meta(IPlugin.Meta):
        inputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    def process(self, df, **kwargs) -> pandas.DataFrame:
        if not "df":
            raise PluginError("Dataframe was not passed to plugin", plugin=self)
        return df


##
## IGroupPlugin
##


class IGroupPlugin(IPlugin):
    """ A plugin that groups multiple plugins into a functional block, eg: a processing pipeline or graph workflow. """

    plugins = []

    def __init__(self, plugins, **kwargs):
        super().__init__(**kwargs)
        self.plugins = plugins


##
## PluginError
##


class PluginError(Exception):
    """ Exception generated by a plugin; carries plugin info, inner exception """

    message: str = None
    plugin: IPlugin = None

    def __init__(self, message, plugin: IPlugin, exception: Exception = None):
        assert plugin
        super().__init__(message, exception)
        self.message = message
        self.plugin = plugin
        plugin.logger.error(message)

    def __str__(self):
        return self.plugin.name + ": " + self.message
