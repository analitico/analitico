# We need to import this library here even though we don't
# use it directly below because we are instantiating the
# plugins by name from globals() and they won't be found if
# this import is not here.
import analitico.plugin

from analitico.dataset import Dataset

##
## PluginManager
##


class PluginManager(analitico.plugin.IPluginManager):
    """ 
    Concrete implementation of analitico plugins manager which implements factory
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
            raise analitico.plugin.PluginError("PluginManager - can't find plugin: " + name)
        return (klass)(manager=self, **kwargs)

    def get_dataset(self, dataset_id):
        """ Creates a Dataset object from the cloud dataset with the given id """
        plugin_settings = {
            "type": "analitico/plugin",
            "name": "analitico.plugin.CsvDataframeSourcePlugin",
            "source": {"type": "text/csv", "url": "analitico://datasets/{}/data/csv".format(dataset_id)},
        }
        # Instead of creating a plugin that reads the end product of the dataset
        # pipeline we should consider reading the dataset information from its endpoint,
        # getting the entire plugin chain and recreating it here exactly the same so it
        # can be run in Jupyter with all its plugins, etc.
        plugin = self.create_plugin(**plugin_settings)
        return Dataset(self, plugin=plugin)
