from abc import ABC, abstractmethod
from .plugin import IPluginManager, PluginError
import logging

import analitico.plugin

##
## PluginManager
##


class PluginManager(IPluginManager):
    """ 
    Concrete implementation of analitico plugins manager which impleents factory
    and life cycle management and orchestration methods for plugins.
    """

    # TODO could register external plugins

    def _get_class_from_fully_qualified_name(self, name, module=None):
        """ Gets a class from its fully qualified name, eg: package.module.Class """
        if name:
            split = name.split(".")
            if len(split) > 1:
                prefix = split[0]
                name = name[len(split[0]) + 1 :]
                module = getattr(module, prefix) if module else globals()[prefix]
                return self._get_class_from_fully_qualified_name(name, module)
            return getattr(module, split[0])
        return None

    def create_plugin(self, name: str, **kwargs):
        """
        Create a plugin given its name and the environment it will run in.
        Any additional parameters passed to this method will be passed to the
        plugin initialization code and will be stored as a plugin setting.
        """
        klass = self._get_class_from_fully_qualified_name(name)
        if not klass:
            raise PluginError("PluginManager - can't find plugin: " + name)
        return (klass)(manager=self, **kwargs)


# Analitico plugins factory
manager: IPluginManager = PluginManager()
