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
    """ A plugin that creates a linear workflow by chaining together other plugins """

    pass


##
## GraphPlugin
##


class GraphPlugin(IGroupPlugin):
    """ A plugin that can join a number of other plugins into a coordinated workflow. """

    pass
