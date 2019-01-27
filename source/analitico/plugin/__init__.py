# plugin base classes
from .plugin import PluginError
from .plugin import IPluginEnvironment, PluginEnvironment
from .plugin import IPlugin

# plugins to generate a dataframe from a source
from .plugin import IDataframeSourcePlugin
from .sources import CsvDataframeSourcePlugin

# plugins that tranform a dataframe
from .plugin import IDataframePlugin
from .transforms import CodeDataframePlugin

# plugin grouping
from .plugin import IGroupPlugin
from .groups import PipelinePlugin
from .groups import GraphPlugin

# plugin factory
from .factory import IPluginFactory, factory

# Constants with plugin names
CSV_DATAFRAME_SOURCE_PLUGIN = CsvDataframeSourcePlugin.Meta.name
CODE_DATAFRAME_PLUGIN = CodeDataframePlugin.Meta.name
PIPELINE_PLUGIN = PipelinePlugin.Meta.name
GRAPH_PLUGIN = GraphPlugin.Meta.name
