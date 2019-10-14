import analitico.utilities
import pandas as pd
import os

from analitico.schema import generate_schema
from .pipelineplugin import PipelinePlugin
from .interfaces import plugin

##
## DataframePipelinePlugin
##


@plugin
class DataframePipelinePlugin(PipelinePlugin):
    """ 
    A ETL pipeline plugin that creates a linear workflow by chaining together other plugins 
    where the final result is a pandas dataframe + its schema (metadata). These get saved
    as artifacts named data.csv (the data) and data.csv.info (the schema).
    """

    class Meta(PipelinePlugin.Meta):
        name = "analitico.plugin.DataframePipelinePlugin"
        inputs = None
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    def run(self, *args, action=None, **kwargs):
        """ Process the plugins in sequence then save the resulting dataframe """
        df = super().run(*args, action=action, **kwargs)
        if not isinstance(df, pd.DataFrame):
            self.logger.warn("DataframePipelinePlugin.run - pipeline didn't produce a valid dataframe")
            return None

        # save dataframe as data.csv
        # we will save the index column only if it is named
        # and it was created explicitely
        artifacts_path = self.factory.get_artifacts_directory()
        csv_path = os.path.join(artifacts_path, "data.csv")
        index = bool(df.index.name)
        df.to_csv(csv_path, index=index)

        # save schema as data.csv.info
        schema = generate_schema(df)
        csv_info_path = csv_path + ".info"
        analitico.utilities.save_json({"schema": schema}, csv_info_path)

        return df
