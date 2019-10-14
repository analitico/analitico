"""
Plugins that import dataframes from different sources
"""

import pandas
from analitico.utilities import get_dict_dot
from analitico.schema import analitico_to_pandas_type, apply_schema, NA_VALUES
from .interfaces import IDataframeSourcePlugin, PluginError, plugin

##
## CsvDataframeSourcePlugin
##


@plugin
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
                info = self.factory.get_url_json(info_url)
                schema = get_dict_dot(info, "data.schema")

            # array of types for each column in the source
            columns = schema.get("columns") if schema else None

            dtype = None
            if columns:
                dtype = {}
                for column in columns:
                    if "type" in column:  # type is optionally defined
                        if column["type"] == "datetime":
                            dtype[column["name"]] = "object"
                        elif column["type"] == "timespan":
                            dtype[column["name"]] = "object"
                        else:
                            dtype[column["name"]] = analitico_to_pandas_type(column["type"])

            stream = self.factory.get_url_stream(url, binary=False)
            df = pandas.read_csv(stream, dtype=dtype, encoding="utf-8", na_values=NA_VALUES)

            tail = self.get_attribute("tail", 0)
            if tail > 0:
                rows_before = len(df)
                df = df.tail(tail)
                self.info("tail: %d, rows before: %d, rows after: %d", tail, rows_before, len(df))

            if schema:
                # reorder, filter, apply types, rename columns as requested in schema
                df = apply_schema(df, schema)

            return df
        except Exception as exc:
            self.exception("Error while processing: %s", url, exception=exc)
