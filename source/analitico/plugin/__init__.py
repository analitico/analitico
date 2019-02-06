# plugin base classes
from .plugin import IPlugin  # NOQA: F401
from .plugin import IDataframeSourcePlugin  # NOQA: F401
from .plugin import IDataframePlugin  # NOQA: F401
from .plugin import IGroupPlugin  # NOQA: F401
from .plugin import IPluginManager  # NOQA: F401
from .plugin import PluginError  # NOQA: F401

# plugins to generate dataframes from sources
from .csvdataframesourceplugin import CsvDataframeSourcePlugin

# plugins to tranform dataframes
from .transforms import CodeDataframePlugin

# plugin workflows
from .pipelineplugin import PipelinePlugin
from .dataframepipelineplugin import DataframePipelinePlugin
from .graphplugin import GraphPlugin

# plugin names
CSV_DATAFRAME_SOURCE_PLUGIN = CsvDataframeSourcePlugin.Meta.name
CODE_DATAFRAME_PLUGIN = CodeDataframePlugin.Meta.name
PIPELINE_PLUGIN = PipelinePlugin.Meta.name
DATAFRAME_PIPELINE_PLUGIN = DataframePipelinePlugin.Meta.name
GRAPH_PLUGIN = GraphPlugin.Meta.name

# analitico type for plugins
PLUGIN_TYPE = "analitico/plugin"

# NOQA: F401 prospector complains that these imports
# are unused but they are here to define the module
