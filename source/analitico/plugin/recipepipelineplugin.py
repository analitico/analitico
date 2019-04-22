import os
import os.path
import pandas as pd

from .interfaces import PluginError
from .pipelineplugin import PipelinePlugin, plugin

import analitico.constants
import analitico.pandas

from analitico import status, AnaliticoException
from analitico.utilities import read_json

##
## RecipePipelinePlugin
##


@plugin
class RecipePipelinePlugin(PipelinePlugin):
    """
    A recipe pipeline contains:
    - a dataframe source plugin that gathers the training data
    - a miminal (or empty) set of plugins to do some final filtering (eg. remove columns)
    - an algorithm used for training (eg. classifier, neural net, etc)
    Running the pipeline produces a trained model which can be used later for predictions.
    """

    class Meta(PipelinePlugin.Meta):
        name = "analitico.plugin.RecipePipelinePlugin"
        inputs = None
        outputs = [{"model": "dict"}]

    def run(self, *args, action=None, **kwargs):
        """ Process the plugins in sequence to create trained model artifacts """
        artifacts_path = self.factory.get_artifacts_directory()
        training_path = os.path.join(artifacts_path, "training.json")

        # when training run the recipe which will produce the training artifacts
        if analitico.constants.ACTION_TRAIN in action:
            results = super().run(*args, action=action, **kwargs)
            # training.json, trained models and other artifacts should
            # now be in the artifacts directory. depending on the environment
            # these may be left on disk (SDK) or stored in cloud (APIs)
            if not isinstance(results, dict):
                self.factory.exception(
                    "Pipeline didn't return a dictionary with training results",
                    item=self,
                    artifacts_path=artifacts_path,
                )
            if not os.path.isfile(training_path):
                self.factory.exception(
                    "Pipeline didn't produce training.json", item=self, artifacts_path=artifacts_path
                )
            return results

        # when predicting pass the data to the recipe for prediction
        if analitico.constants.ACTION_PREDICT in action:
            # check for training information on disk
            if not os.path.isfile(training_path):
                self.factory.exception(
                    "Pipeline can't fine file training.json", item=self, artifacts_path=artifacts_path
                )

            # normally prediction input is a pd.DataFrame
            if isinstance(args[0], pd.DataFrame):
                df_original = args[0]  # original data
                df = df_original.copy()  # df processed inplace
                predictions = super().run(df, action=action, **kwargs)
            else:
                # run the pipeline with generic input return predictions
                predictions = super().run(*args, action=action, **kwargs)
            return predictions

        # let the factory raise the exception so it can fill it with context
        self.factory.exception("RecipePipelinePlugin doesn't implement action: %s", action, plugin=self)
