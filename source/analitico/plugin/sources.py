"""
Plugins that import dataframes from different sources
"""

import pandas
from .plugin import IDataframePlugin, PluginError

import pandas
from analitico.utilities import analitico_to_pandas_type
from .plugin import IDataframeSourcePlugin, PluginError

##
## CsvDataframeSourcePlugin
##


class CsvDataframeSourcePlugin(IDataframeSourcePlugin):
    """ A plugin that returns a pandas dataframe from a csv file """

    class Meta(IDataframeSourcePlugin.Meta):
        name = "analitico.plugin.CsvDataframeSourcePlugin"

    def process(self, **kwargs):
        """ Creates a pandas dataframe from the csv source """
        try:
            schema = self.settings.get("schema")
            columns = schema.get("columns") if schema else None

            dtype = None
            parse_dates = None
            index = None

            if columns:
                dtype = {}
                parse_dates = []
                for idx, column in enumerate(columns):
                    if column["type"] == "datetime":
                        # ISO8601 dates only for now
                        # TODO use converters to apply date patterns #16
                        parse_dates.append(idx)
                    elif column["type"] == "timespan":
                        # timedelta needs to be applied later on or else we will get:
                        # 'the dtype timedelta64 is not supported for parsing'
                        dtype[column["name"]] = "object"
                    else:
                        dtype[column["name"]] = analitico_to_pandas_type(column["type"])
                    if column.get("index", False):
                        index = column["name"]

            url = self.settings.get("url")
            if not url:
                raise PluginError("URL of csv file cannot be empty.", plugin=self)
            df = pandas.read_csv(url, dtype=dtype, parse_dates=parse_dates, **kwargs)

            if index:
                # transform specific column with unique values to dataframe index
                df = df.set_index(index, drop=False)

            if columns:
                names = []
                for column in columns:
                    # check if we need to cast timedelta which we had left as strings
                    if column["type"] == "timespan":
                        name = column["name"]
                        df[name] = pandas.to_timedelta(df[name])
                    names.append(column["name"])
                # reorder and filter columns as requested in schema
                df = df[names]
            return df
        except Exception as exc:
            raise PluginError("Error while processing " + url, self, exc)
