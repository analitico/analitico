import pandas as pd

import analitico.pandas
import analitico.utilities

from analitico.constants import ACTION_TRAIN
from analitico.utilities import time_ms, timeit, get_dict_dot

from .interfaces import IDataframeSourcePlugin, plugin

##
## DatasetSourcePlugin
##


@plugin
class DatasetSourcePlugin(IDataframeSourcePlugin):
    """ A plugin that returns data from an analitico dataset """

    class Meta(IDataframeSourcePlugin.Meta):
        name = "analitico.plugin.DatasetSourcePlugin"

    @timeit
    def retrieve_df(self, *args, action=None, **kwargs):
        """ Retrieve dataframe from dataset with id set in plugin's configuration """
        try:
            dataset_id = self.get_attribute("dataset_id")
            if not dataset_id:
                dataset_id = self.get_attribute("source.dataset_id")
                if not dataset_id:
                    self.exception("DatasetSourcePlugin - must specify 'dataset_id'")

            info_url = "analitico://datasets/" + dataset_id + "/data/info"
            self.info("reading: %s", info_url)

            info = self.factory.get_url_json(info_url)
            schema = get_dict_dot(info, "data.schema", None)
            if not schema:
                self.warning("DatasetSourcePlugin - %s does not contain schema information", info_url)

            # save the schema for the source so it can be used to enforce it on prediction
            self.set_attribute("source.schema", schema)

            # stream data from dataset endpoint or storage as csv
            csv_url = "analitico://datasets/" + dataset_id + "/data/csv"
            csv_stream = self.factory.get_url_stream(csv_url, binary=False)

            reading_on = time_ms()
            self.info("reading: %s", csv_url)
            df = analitico.pandas.pd_read_csv(csv_stream, schema)
            self.info("%d rows in %d ms", len(df), time_ms(reading_on))

            # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.sample.html
            sample = self.get_attribute("sample", 0)
            if sample > 0:
                rows_before = len(df)
                df = analitico.pandas.pd_sample(df, sample)
                self.info("sample: %f, rows before: %d, rows after: %d", sample, rows_before, len(df))

            tail = self.get_attribute("tail", 0)
            if tail > 0:
                rows_before = len(df)
                df = df.tail(tail)
                self.info("tail: %d, rows before: %d, rows after: %d", tail, rows_before, len(df))

            return df

        except Exception as exc:
            raise exc

    def run(self, *args, action=None, **kwargs):
        """ Read data from configured dataset in training mode, noop in prediction mode """

        # DEPRECATED in training one may leave this plugin in but pass a dataframe for inference
        # so that the same pipeline can be reused for training and prediction. in this case we will
        # do nothing and pass data through
        if len(args) > 0 and isinstance(args[0], pd.DataFrame):
            self.factory.warning("DatasetSourcePlugin - passed a DataFrame as input, will noop")
            return args[0]

        return self.retrieve_df(*args, action, **kwargs)
