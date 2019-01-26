
from abc import ABC, abstractmethod

from .plugin import IPlugin, IPluginEnvironment, PluginException
from .plugin import CsvDataframeSourcePlugin

##
## IPluginFactory
##

class IPluginFactory(ABC):
    """ Abstract base class for a plugin factory that can find and create plugin instances """
    @abstractmethod
    def create_plugin(self, name: str, environment: IPluginEnvironment, **kwargs):
        """ Find an plugin by name then create and return an instance of it """
        pass

##
## PluginFactory
##

class PluginFactory(IPluginFactory):
    """ Concrete implementation of analitico plugins factory """

    _plugins = {
        'analitico.plugins.csvdataframesourceplugin': CsvDataframeSourcePlugin
    }

    def create_plugin(self, name: str, environment: IPluginEnvironment = None, **kwargs):
        if name.lower() in self._plugins:
            return self._plugins[name.lower()](environment=environment, **kwargs)
        raise PluginException('PluginFactory.create_plugin - could not find plugin: ' + name)


# Analitico plugins factory
pluginFactory: IPluginFactory = PluginFactory()
