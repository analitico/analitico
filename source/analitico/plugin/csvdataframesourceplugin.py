"""
Plugins that import dataframes from different sources
"""

import requests
import pandas
from analitico.utilities import analitico_to_pandas_type, get_dict_dot
from .plugin import IDataframeSourcePlugin, PluginError

##
## CsvDataframeSourcePlugin
##


class CsvDataframeSourcePlugin(IDataframeSourcePlugin):
    """ A plugin that returns a pandas dataframe from a csv file """

    class Meta(IDataframeSourcePlugin.Meta):
        name = "analitico.plugin.CsvDataframeSourcePlugin"

    def run(self, *args, **kwargs):
        """ Creates a pandas dataframe from the csv source """
        try:
            url = self.get_attribute("source.url")
            if not url:
                raise PluginError("URL of csv file cannot be empty.", plugin=self)

            # source schema is part of the source definition?
            schema = self.get_attribute("source.schema")

            # no schema was provided but the url is that of an analitico dataset in the cloud
            if not schema and url.startswith("analitico://") and url.endswith("/data/csv"):
                info_url = url.replace("/data/csv", "/data/info")
                info = self.manager.get_url_json(info_url)
                schema = get_dict_dot(info, "data.schema")

            # array of types for each column in the source
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

            url = self.get_attribute("source.url")
            if not url:
                raise PluginError("URL of csv file cannot be empty.", plugin=self)
            stream = self.manager.get_url_stream(url)
            df = pandas.read_csv(stream, dtype=dtype, parse_dates=parse_dates)

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
