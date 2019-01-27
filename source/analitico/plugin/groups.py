"""
Plugins that group other plugins into logical groups like
ETL (extract, transform, load) pipeline or a graph used to
process data and create a machine learning model.
"""

import pandas
from .plugin import IGroupPlugin, PluginError

import pandas
from analitico.utilities import analitico_to_pandas_type
from .plugin import IDataframeSourcePlugin, PluginError

##
## PipelinePlugin
##


class PipelinePlugin(IGroupPlugin):
    """ 
    A plugin that creates a linear workflow by chaining together other plugins.
    Plugins that are chained in a pipeline need to take a single input and have
    a single output of the same kind so they same object can be processed from 
    the first, to the next and down to the last, then returned to caller as if
    the process was just one logical operation. PipelinePlugin can be used to 
    for example to construct ETL (extract, transform, load) workflows.
    """

    class Meta(IGroupPlugin.Meta):
        name = "analitico.plugin.PipelinePlugin"

    def process(self, **kwargs):
        """ Process plugins in sequence, return combinined result """

        for plugin in self.plugins:
            pass

        return None


##
## GraphPlugin
##


class GraphPlugin(IGroupPlugin):
    """ A plugin that can join a number of other plugins into a coordinated workflow. """

    class Meta(IGroupPlugin.Meta):
        name = "analitico.plugin.GraphPlugin"
