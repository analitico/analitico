# plugin base classes
from .plugin import IPlugin
from .plugin import IDataframeSourcePlugin
from .plugin import IDataframePlugin
from .plugin import IGroupPlugin
from .plugin import IPluginManager
from .plugin import PluginError

# plugins to generate a dataframe from a source
from .sources import CsvDataframeSourcePlugin

# plugins that tranform a dataframe
from .transforms import CodeDataframePlugin

# plugin grouping
from .groups import PipelinePlugin
from .groups import GraphPlugin

# plugin factory
from .manager import PluginManager, manager

# Constants with plugin names
CSV_DATAFRAME_SOURCE_PLUGIN = CsvDataframeSourcePlugin.Meta.name
CODE_DATAFRAME_PLUGIN = CodeDataframePlugin.Meta.name
PIPELINE_PLUGIN = PipelinePlugin.Meta.name
GRAPH_PLUGIN = GraphPlugin.Meta.name

PLUGIN_TYPE = "analitico/plugin"
