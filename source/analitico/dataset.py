import pandas as pd
import numpy as np

import analitico.mixin
import analitico.plugin

from analitico.utilities import pandas_to_analitico_type

##
## Dataset
##


class Dataset(analitico.mixin.SettingsMixin):
    """ A dataset can retrieve data from a source and process it through a pipeline to generate a dataframe """

    plugin: analitico.plugin.IPlugin = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "plugin" in kwargs:
            self.plugin = kwargs["plugin"]
            if isinstance(self.plugin, dict):
                self.plugin = analitico.plugin.manager.create_plugin(**self.plugin)

    @property
    def id(self) -> str:
        return self.get_settings("id")

    def get_dataframe(self, **kwargs):
        """ Creates a pandas dataframe from the plugin of this dataset (usually a source or pipeline) """
        if self.plugin:
            df = self.plugin.process(**kwargs)
            assert isinstance(df, pd.DataFrame)
            return df
        return None

    @staticmethod
    def generate_schema(df: pd.DataFrame) -> dict:
        """ Generates an analitico schema from a pandas dataframe """
        columns = []
        for name in df.columns:
            ctype = pandas_to_analitico_type(df[name].dtype)
            column = {"name": name, "type": ctype}
            if df.index.name == name:
                column["index"] = True
            columns.append(column)
        return {"columns": columns}
