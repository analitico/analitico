from abc import ABC, abstractmethod
from .plugin import IPluginEnvironment
from .csvdataframesourceplugin import CsvDataframeSourcePlugin
from .codedataframeplugin import CodeDataframePlugin

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
        CsvDataframeSourcePlugin.Meta.name: CsvDataframeSourcePlugin,
        CodeDataframePlugin.Meta.name: CodeDataframePlugin,
    }

    def create_plugin(
        self, name: str, environment: IPluginEnvironment = None, **kwargs
    ):
        """
        Create a plugin given its name and the environment it will run in.
        Any additional parameters passed to this method will be passed to the
        plugin initialization code and will be stored as a plugin setting.
        """
        if name.lower() in self._plugins:
            return self._plugins[name.lower()](environment=environment, **kwargs)
        raise Exception("PluginFactory.create_plugin - could not find plugin: " + name)


# Analitico plugins factory
pluginFactory: IPluginFactory = PluginFactory()
