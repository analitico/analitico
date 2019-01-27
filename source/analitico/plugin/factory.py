from abc import ABC, abstractmethod
from .plugin import IPluginEnvironment
import logging

import analitico.plugin

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

    # TODO could register external plugins

    def _get_class_from_fully_qualified_name(self, name, module=None):
        """ Gets a class from its fully qualified name, eg: package.module.Classhat.something """
        if name:
            split = name.split(".")
            if len(split) > 1:
                prefix = split[0]
                name = name[len(split[0]) + 1 :]
                module = getattr(module, prefix) if module else globals()[prefix]
                return self._get_class_from_fully_qualified_name(name, module)
            return getattr(module, split[0])
        return None

    def create_plugin(self, name: str, env: IPluginEnvironment = None, **kwargs):
        """
        Create a plugin given its name and the environment it will run in.
        Any additional parameters passed to this method will be passed to the
        plugin initialization code and will be stored as a plugin setting.
        """
        klass = self._get_class_from_fully_qualified_name(name)
        if not klass:
            raise KeyError("PluginFactory - can't find plugin: " + name)
        return (klass)(env=env, **kwargs)


# Analitico plugins factory
factory: IPluginFactory = PluginFactory()
