import os
import os.path
import pandas as pd

import analitico.pandas
from analitico.utilities import read_json, get_dict_dot

from .interfaces import plugin
from .pipelineplugin import PipelinePlugin

##
## EndpointPipelinePlugin
##


@plugin
class EndpointPipelinePlugin(PipelinePlugin):
    """
    EndpointPipelinePlugin is a base class for endpoints that take trained machine
    learning models to deliver inferences. An endpoint subclass could implement 
    inference APIs by taking a web request and returning predictions, etc.
    """

    class Meta(PipelinePlugin.Meta):
        name = "analitico.plugin.EndpointPipelinePlugin"
        inputs = [{"data": "pandas.DataFrame"}]
        outputs = [{"predictions": "pandas.DataFrame"}]

    def run(self, *args, action=None, **kwargs):
        """ Process the plugins in sequence to run predictions """
        try:
            # if no plugins have been configured for the pipeline,
            # create the plugin suggested by the training algorithm
            if not self.plugins:
                # read training information from disk
                artifacts_path = self.factory.get_artifacts_directory()
                training_path = os.path.join(artifacts_path, "training.json")
                training = read_json(training_path)
                assert training
                self.set_attribute("plugins", [{"name": get_dict_dot(training, "plugins.prediction")}])

            assert isinstance(args[0], pd.DataFrame)
            df = args[0]
            df_copy = df.copy()

            # run the pipeline, return predictions
            predictions = super().run(df, action=action, **kwargs)

            # the predictor has most likely added a "records" field with the processed
            # records which we may choose to avoid echoing back to the caller. if we want
            # we can remove the records here before returning

            return predictions

        except Exception as exc:
            self.error("Error while processing prediction pipeline")
            self.logger.exception(exc)
            raise exc
