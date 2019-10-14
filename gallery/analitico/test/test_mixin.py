import json
import os
import os.path

import analitico.dataset
import analitico.utilities
import analitico.plugin

from analitico.dataset import Dataset

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets"


class TestMixin:
    """ Basic unit testing functionality for analitico's tests """

    # Create default factory
    factory = analitico.authorize()

    def get_asset_path(self, path):
        """ Returns absolute path of file in test /assets directory """
        return os.path.join(ASSETS_PATH, path)

    def read_json_asset(self, path):
        with open(self.get_asset_path(path), "r") as f:
            text = f.read()
            text = text.replace("{assets}", ASSETS_PATH)
            return json.loads(text)

    def read_dataset_asset(self, path):
        json = self.read_json_asset(path)
        return Dataset(factory=self.factory, **json)

    def read_dataframe_asset(self, path):
        ds = self.read_dataset_asset(path)
        return ds.get_dataframe()

    def get_csv_plugin(self, **kwargs):
        name = analitico.plugin.CSV_DATAFRAME_SOURCE_PLUGIN
        return self.factory.get_plugin(name, **kwargs)
