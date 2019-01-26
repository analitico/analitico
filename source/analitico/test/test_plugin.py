import unittest
import os
import os.path

import pandas as pd

import analitico.plugin
import analitico.utilities

from analitico.plugin import PluginException, PluginEnvironment
from analitico.plugin import CsvDataframeSourcePlugin, CodeDataframePlugin
from analitico.plugin import pluginFactory

from .utilities import TestUtilitiesMixin

# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets"


class PluginTests(unittest.TestCase, TestUtilitiesMixin):
    """ Unit testing of Plugin functionalities """

    env = PluginEnvironment()

    def test_plugin_basics_settings(self):
        """ Test plugin settings """
        try:
            plugin = CsvDataframeSourcePlugin(param1="value1", param2="value2")

            self.assertEqual(plugin.param1, "value1")
            self.assertEqual(plugin.param2, "value2")

            self.assertEqual(plugin.get_setting("param1"), "value1")
            self.assertEqual(plugin.get_setting("param2"), "value2")
        except Exception as exc:
            raise exc

    def test_plugin_factory(self):
        try:
            env = PluginEnvironment()
            plugin = pluginFactory.create_plugin(
                CsvDataframeSourcePlugin.Meta.name,
                env,
                param1="value1",
                param2="value2",
            )

            self.assertEqual(plugin.param1, "value1")
            self.assertEqual(plugin.param2, "value2")
            self.assertEqual(plugin.get_setting("param1"), "value1")
            self.assertEqual(plugin.get_setting("param2"), "value2")
        except Exception as exc:
            raise exc

    def test_plugin_csv_read(self):
        """ Test using csv plugin to read basic csv file """
        csv_url = self.get_asset_path("ds_test_1.csv")
        csv_plugin = self.get_csv_plugin(url=csv_url)
        self.assertTrue(isinstance(csv_plugin, CsvDataframeSourcePlugin))
        self.assertEqual(csv_plugin.url, csv_url)

        df = csv_plugin.process()
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 3)

    def test_plugin_code_dataframe_basic(self):
        """ Test using csv plugin to applies basic code to a dataframe """
        csv_url = self.get_asset_path("ds_test_1.csv")
        csv_plugin = self.get_csv_plugin(url=csv_url)

        df = csv_plugin.process()
        self.assertEqual(df.loc[0, "First"], 10)

        # configure plugin to add 2 to all values in the first column of the dataframe
        code = "df['First'] = df['First'] + 2"
        transform_plugin = pluginFactory.create_plugin(
            CodeDataframePlugin.Meta.name, environment=self.env, code=code
        )

        df = transform_plugin.process(df=df)
        self.assertEqual(df.loc[0, "First"], 12)

        df = transform_plugin.process(df=df)
        self.assertEqual(df.loc[0, "First"], 14)

    def test_plugin_code_dataframe_bug(self):
        """ Test using csv plugin to applies code with a bug to a dataframe """
        csv_url = self.get_asset_path("ds_test_1.csv")
        csv_plugin = self.get_csv_plugin(url=csv_url)

        df = csv_plugin.process()
        self.assertEqual(df.loc[0, "First"], 10)

        # refers to df2 which DOES NOT exist
        code = "df['First'] = df2['First'] + 2"
        transform_plugin = pluginFactory.create_plugin(
            CodeDataframePlugin.Meta.name, environment=self.env, code=code
        )

        with self.assertRaises(PluginException):
            df = transform_plugin.process(df=df)
