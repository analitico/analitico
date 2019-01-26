import unittest
import json
import os
import os.path
import datetime

import pandas as pd

import analitico.dataset
import analitico.utilities

from analitico.dataset import Dataset, ds_factory
from analitico.utilities import read_json, get_dict_dot
from analitico.plugin import PluginEnvironment, pluginFactory
from analitico.plugin import CsvDataframeSourcePlugin

# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets"


class TestUtilitiesMixin:
    """ Basic unit testing functionality for analitico's tests """

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
        return ds_factory(**json)

    def read_dataframe_asset(self, path):
        ds = self.read_dataset_asset(path)
        return ds.get_dataframe()

    def get_csv_plugin(self, **kwargs):
        env = PluginEnvironment()
        return pluginFactory.create_plugin(
            CsvDataframeSourcePlugin.Meta.name, env, **kwargs
        )
