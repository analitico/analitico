import pandas as pd
import analitico.pandas
import analitico.schema

from .interfaces import IDataframePlugin, plugin

##
## AugmentDatesPlugin - dataframe in, dataframe out with better dates
##

ERROR_WHILE_AUGMENTING = "An error occoured while augmenting columns"
ERROR_WHILE_AUGMENTING_COL = "An error occoured while augmenting column: %s"
ERROR_COL_NOT_FOUND = "AugmentDatesPlugin - column '%s' was not found."


@plugin
class AugmentDatesPlugin(IDataframePlugin):
    """ A plugin that takes dates and turns them into .year, .month, .day, .dayofweek, .hour and .min columns. """

    class Meta(IDataframePlugin.Meta):
        name = "analitico.plugin.AugmentDatesPlugin"
        title = "AugmentDatesPlugin"
        description = "A plugin used to expand datetime columns into year, month, day, dayofweek, hour and minutes."
        configurations = [
            {
                "name": "schema",
                "type": "analitico/schema",
                "optional": True,
                "description": "A schema can be passed to indicate which columns should be augmented. If no schema is passed, the plugin will augment all datatime columns in the dataframe.",
            }
        ]

    def run(self, *args, action=None, **kwargs):
        try:
            df = args[0]
            if df is not None and isinstance(df, pd.DataFrame):
                columns = self.get_attribute("schema.columns")
                if columns:
                    # if columns were specified act only on those columns
                    for column in columns:
                        if "name" in column:
                            try:
                                column_name = column["name"]
                                if column["name"] in df:
                                    analitico.pandas.pd_cast_datetime(df, column_name)
                                    analitico.pandas.pd_augment_date(df, column_name)
                            except Exception as exc:
                                self.exception(ERROR_WHILE_AUGMENTING_COL, column_name, exception=exc)

                        else:
                            self.warning(ERROR_COL_NOT_FOUND, column_name)
                else:
                    # if schema was not specified just scan all columns and expand those that are datetime
                    for column in df.columns:
                        if df[column].dtype.name == analitico.schema.PD_TYPE_DATETIME:
                            analitico.pandas.pd_augment_date(df, column)
            return df
        except Exception as exc:
            self.exception(ERROR_WHILE_AUGMENTING, exception=exc)
