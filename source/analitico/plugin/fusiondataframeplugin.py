import pandas as pd

from analitico.pandas import pd_columns_to_string
from .interfaces import PluginError, IDataframePlugin
from .pipelineplugin import PipelinePlugin, plugin

##
## FusionDataframePlugin
##

ERROR_NO_INPUT_DF = "Should receive as input a single pd.DataFrame, received: %s"
ERROR_NO_PIPELINE_DF = (
    "Plugins pipeline should produce a pd.DataFrame to be merged with main input, instead received: %s"
)
ERROR_NO_LEFT_COLUMN = (
    "The left (main) dataframe does not have a column named '%s' to merge on. Available columns are: %s."
)
ERROR_NO_RIGHT_COLUMN = (
    "The right (secondary) dataframe does not have a column named '%s' to merge on. Available columns are: %s."
)
ERROR_NO_MERGE_CONF = "You need to specify how to merge dataframes either with the 'on' attribute or with the 'left_on' and 'right_on' attributes indicating the column names"


@plugin
class FusionDataframePlugin(PipelinePlugin):
    """ 
    A plugin used to merge two datasources using specific merge rules.
    This plugin is a IDataframePlugin because it takes a dataframe
    (the main table or left table), modifies it (join) and returns it.
    It is also a DataframePipelinePlugin because it can embed a second
    pipeline which generates the secondary, or right, table which is
    merged with the main. Merging is performed based on rules described 
    in the "merge" attribute, which is a dictionary that closely maps
    pandas' merge parameters.
    """

    class Meta(IDataframePlugin.Meta):
        name = "analitico.plugin.FusionDataframePlugin"
        inputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    def run(self, *args, action=None, **kwargs) -> pd.DataFrame:
        """ Merge two pipelines into a single dataframe """
        try:
            df_left = args[0]
            if not isinstance(df_left, pd.DataFrame):
                self.exception(ERROR_NO_INPUT_DF, df_left)

            # run the pipeline to obtain the secondary table (right) that we're joining on
            df_right = super().run(action=action, **kwargs)
            if not isinstance(df_right, pd.DataFrame):
                self.exception(ERROR_NO_PIPELINE_DF, df_right)

            self.info("Left columns: %s", pd_columns_to_string(df_left))
            self.info("Left rows: %d", len(df_left))
            self.info("Right columns: %s", pd_columns_to_string(df_right))
            self.info("Right rows: %d", len(df_right))

            # "merge" attribute contains a dictionary of settings that closely match those of pandas.merge:
            # https://pandas.pydata.org/pandas-docs/stable/user_guide/merging.html#database-style-dataframe-or-named-series-joining-merging

            merge = self.get_attribute("merge")
            if not merge:
                self.exception("Attribute 'merge' with merging details is required")

            # "how" determines how we merge
            how = merge.get("how", "inner")
            how_options = ["left", "right", "outer", "inner"]
            if how not in how_options:
                self.exception("Attribute how: %s is unknown, should be one of %s", how, str(how_options))

            on = merge.get("on", None)
            if on:
                self.info("Merge on: %s", on)

                if on not in df_left.columns:
                    self.exception(ERROR_NO_LEFT_COLUMN, on, pd_columns_to_string(df_left))
                if on not in df_right.columns:
                    self.exception(ERROR_NO_RIGHT_COLUMN, on, pd_columns_to_string(df_right))

                df_fusion = pd.merge(df_left, df_right, on=on, how=how)

            else:
                left_on = merge.get("left_on", None)
                right_on = merge.get("right_on", None)

                if left_on and right_on:
                    self.info("Merge left_on: %s, right_on: %s", left_on, right_on)
                    if left_on not in df_left.columns:
                        self.exception(ERROR_NO_LEFT_COLUMN, left_on, pd_columns_to_string(df_left))
                    if right_on not in df_right.columns:
                        self.exception(ERROR_NO_RIGHT_COLUMN, right_on, pd_columns_to_string(df_right))

                    df_fusion = pd.merge(df_left, df_right, left_on=left_on, right_on=right_on, how=how)
                else:
                    self.exception(ERROR_NO_MERGE_CONF)

            return df_fusion

        except PluginError as plugin_error:
            raise plugin_error
        except Exception as exc:
            self.exception("Exception while merging dataframes", exception=exc)
