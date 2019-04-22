# plugin base classes
from .interfaces import *

# plugins to generate dataframes from sources
from .csvdataframesourceplugin import CsvDataframeSourcePlugin
from .datasetsourceplugin import DatasetSourcePlugin

# plugins to tranform dataframes
from .transforms import CodeDataframePlugin
from .augmentdatesplugin import AugmentDatesPlugin
from .fusiondataframeplugin import FusionDataframePlugin
from .transformdataframeplugin import TransformDataframePlugin

# machine learning algorithms
from .catboostplugin import CatBoostPlugin
from .catboostplugin import CatBoostRegressorPlugin
from .catboostplugin import CatBoostClassifierPlugin

# plugin workflows
from .pipelineplugin import PipelinePlugin
from .dataframepipelineplugin import DataframePipelinePlugin
from .recipepipelineplugin import RecipePipelinePlugin
from .endpointpipelineplugin import EndpointPipelinePlugin

CSV_DATAFRAME_SOURCE_PLUGIN = CsvDataframeSourcePlugin.Meta.name
DATASET_SOURCE_PLUGIN = DatasetSourcePlugin.Meta.name
CODE_DATAFRAME_PLUGIN = CodeDataframePlugin.Meta.name
AUGMENT_DATES_PLUGIN = AugmentDatesPlugin.Meta.name
FUSION_DATAFRAME_PLUGIN = FusionDataframePlugin.Meta.name
TRANSFORM_DATAFRAME_PLUGIN = TransformDataframePlugin.Meta.name
CATBOOST_PLUGIN = CatBoostPlugin.Meta.name
CATBOOST_REGRESSOR_PLUGIN = CatBoostRegressorPlugin.Meta.name
CATBOOST_CLASSIFIER_PLUGIN = CatBoostClassifierPlugin.Meta.name
PIPELINE_PLUGIN = PipelinePlugin.Meta.name
DATAFRAME_PIPELINE_PLUGIN = DataframePipelinePlugin.Meta.name
RECIPE_PIPELINE_PLUGIN = RecipePipelinePlugin.Meta.name
ENDPOINT_PIPELINE_PLUGIN = EndpointPipelinePlugin.Meta.name

# analitico type for plugins
PLUGIN_TYPE = "analitico/plugin"

# NOQA: F401 prospector complains that these imports
# are unused but they are here to define the module
