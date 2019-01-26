import unittest
import os
import os.path

import pandas as pd

import analitico.plugin
import analitico.utilities

from analitico.plugin import PluginException, PluginEnvironment
from analitico.plugin import CsvDataframeSourcePlugin
from analitico.plugin import pluginFactory

from .utilities import TestUtilitiesMixin

# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + '/assets'

class PluginTests(unittest.TestCase, TestUtilitiesMixin):
    """ Unit testing of Plugin functionalities """

    def test_plugin_basics_settings(self):
        """ Test plugin settings """
        try:
            plugin = CsvDataframeSourcePlugin(param1='value1', param2='value2')

            self.assertEqual(plugin.param1, 'value1')
            self.assertEqual(plugin.param2, 'value2')

            self.assertEqual(plugin.get_setting('param1'), 'value1')
            self.assertEqual(plugin.get_setting('param2'), 'value2')
        except Exception as exc:
            raise exc


    def test_plugin_factory(self):
        try:
            env = PluginEnvironment()
            plugin = pluginFactory.create_plugin(CsvDataframeSourcePlugin.Meta.name, env, param1='value1', param2='value2')

            self.assertEqual(plugin.param1, 'value1')
            self.assertEqual(plugin.param2, 'value2')
            self.assertEqual(plugin.get_setting('param1'), 'value1')
            self.assertEqual(plugin.get_setting('param2'), 'value2')
        except Exception as exc:
            raise exc


    def test_plugin_csv_read(self):
        """ Test using csv plugin to read basic csv file """
        csv_url = self.get_asset_path('ds_test_1.csv')
        csv_plugin = self.get_csv_plugin(url=csv_url)
        self.assertTrue(isinstance(csv_plugin, CsvDataframeSourcePlugin))
        self.assertEqual(csv_plugin.url, csv_url)

        df = csv_plugin.run()
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 3)
