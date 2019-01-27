# plugin base classes
from .plugin import IPlugin # NOQA: F401
from .plugin import IDataframeSourcePlugin # NOQA: F401
from .plugin import IDataframePlugin # NOQA: F401
from .plugin import IGroupPlugin # NOQA: F401
from .plugin import IPluginManager # NOQA: F401
from .plugin import PluginError # NOQA: F401

# plugins to generate a dataframe from a source
from .sources import CsvDataframeSourcePlugin

# plugins that tranform a dataframe
from .transforms import CodeDataframePlugin

# plugin grouping
from .groups import PipelinePlugin
from .groups import GraphPlugin

# plugin factory
from .manager import PluginManager, manager # NOQA: F401

# Constants with plugin names
CSV_DATAFRAME_SOURCE_PLUGIN = CsvDataframeSourcePlugin.Meta.name
CODE_DATAFRAME_PLUGIN = CodeDataframePlugin.Meta.name
PIPELINE_PLUGIN = PipelinePlugin.Meta.name
GRAPH_PLUGIN = GraphPlugin.Meta.name

PLUGIN_TYPE = "analitico/plugin"

# NOQA: F401 prospector complains that these imports 
# are unused but they are here to define the module
