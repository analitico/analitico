
from abc import ABC, abstractmethod

import logging
import pandas

from analitico.utilities import analitico_to_pandas_type

# Possible frameworks/utilities
# https://github.com/pytest-dev/pluggy/
# http://yapsy.sourceforge.net/


# General concepts:
# - plugins can contain code that we write
# - plugins will contain code from 3rd parties that runs in process (after checks)
# - plugins will contain untrusted code (needs to be isolated)
# - plugins may have specific requirements.txt for their dependencies
# - execution has the concept of environment, variables, etc
# - execution has the concept of stages: preflight/sampling, training, testing, inference

## basic plugin class
# - input parameters metadata
# - output parameters metadata
# - id, type, category, description, etc...
# - configurations and settings
# - process input -> output

## dataset plugin
# - inputs is a single dataset (or source)
# - output is a single dataset

## dataset pipeline (maybe is a plugin itself that aggregates)
# - array of plugins and configurations
# - process entire pipeline at once

## recipe plugin
# - output: a trained model
# - output: training statistics (accuracy, etc?)

## trained model
# - input: dataset
# - output: predictions

##
## SettingsMixin
##

class SettingsMixin():
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

    def get_setting(self, setting):
        return self._settings.get(setting, None)

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
        pass

    environment = None

    @property
    def name(self):
        return type(self).__name__

    @property
    def logger(self):
        """ Logger that can be used by the plugin to communicate errors, etc with host """
        return logging.getLogger(self.name)

    def __init__(self, environment: IPluginEnvironment = None, **kwargs):
        super().__init__(**kwargs)
        self.environment = environment

    def activate(self, **kwargs):
        """ Called when the plugin is initially activated """
        pass

    @abstractmethod
    def run(self, **kwargs):
        """ Run will do in the subclass whatever the plugin does """
        pass

    def deactivate(self, **kwargs):
        """ Called before the plugin is deactivated and finalized """
        pass

    def __str__(self):
        return self.name


##
## PluginException
##

class PluginException(Exception):
    plugin: IPlugin = None
    def __init__(self, message, exception: Exception = None, plugin: IPlugin = None):
        if plugin:
            message = plugin.name + ': ' + message
        super().__init__(message, exception)
        self.plugin = plugin


##
## IDataframeSourcePlugin - base class for plugins that create dataframes
##

class IDataframeSourcePlugin(IPlugin):
    """ A plugin that creates a pandas dataframe from a source (eg: csv file, sql query, etc) """
    class Meta(IPlugin.Meta):
        inputs = None
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]


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


##
## CsvDataframeSourcePlugin
##

class CsvDataframeSourcePlugin(IDataframeSourcePlugin):
    """ A plugin that returns a pandas dataframe from a csv file """

    def run(self, **kwargs):
        """ Creates a pandas dataframe from the csv source """
        try:
            schema = self.settings.get('schema')
            columns = schema.get('columns') if schema else None

            dtype = None
            parse_dates = None
            index = None

            if columns:
                dtype = {}
                parse_dates = []
                for idx, column in enumerate(columns):
                    if column['type'] == 'datetime':
                        parse_dates.append(idx) # ISO8601 dates only
                    elif column['type'] == 'timespan':
                        # timedelta needs to be applied later on or else we will get
                        # 'the dtype timedelta64 is not supported for parsing'
                        dtype[column['name']] = 'object'
                    else:
                        dtype[column['name']] = analitico_to_pandas_type(column['type'])
                    if column.get('index', False):
                        index = column['name']

            url = self.settings.get('url')
            if not url:
                raise PluginException('URL of csv file cannot be empty.')
            df = pandas.read_csv(url, dtype=dtype, parse_dates=parse_dates, **kwargs)

            if index:
                # transform specific column with unique values to dataframe index
                df = df.set_index(index, drop=False)

            if columns:
                names = []
                for column in columns:
                    # check if we need to cast timedelta which we had left as strings
                    if column['type'] == 'timespan':
                        name = column['name']
                        df[name] = pandas.to_timedelta(df[name])
                    names.append(column['name'])
                # reorder and filter columns as requested in schema
                df = df[names]

            return df
        except Exception as exc:
            self.logger.error('CsvDataframeSourcePlugin.run: %s', str(exc))
            raise exc
