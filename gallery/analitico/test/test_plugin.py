import unittest
import os
import os.path
import pytest
import pandas as pd

from analitico.plugin import PluginError, PLUGIN_TYPE
from analitico.plugin import CsvDataframeSourcePlugin, CSV_DATAFRAME_SOURCE_PLUGIN
from analitico.plugin import CODE_DATAFRAME_PLUGIN
from analitico.plugin import PipelinePlugin, PIPELINE_PLUGIN

from .test_mixin import TestMixin

# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets"


@pytest.mark.django_db
class PluginTests(unittest.TestCase, TestMixin):
    """ Unit testing of Plugin functionalities """

    def test_plugin_basics_settings(self):
        """ Test plugin settings """
        try:
            plugin = CsvDataframeSourcePlugin(factory=self.factory, param1="value1", param2="value2")

            self.assertEqual(plugin.param1, "value1")
            self.assertEqual(plugin.param2, "value2")

            self.assertEqual(plugin.get_attribute("param1"), "value1")
            self.assertEqual(plugin.get_attribute("param2"), "value2")
        except Exception as exc:
            raise exc

    def test_plugin_factory(self):
        try:
            plugin = self.factory.get_plugin(CSV_DATAFRAME_SOURCE_PLUGIN, param1="value1", param2="value2")

            self.assertEqual(plugin.param1, "value1")
            self.assertEqual(plugin.param2, "value2")
            self.assertEqual(plugin.get_attribute("param1"), "value1")
            self.assertEqual(plugin.get_attribute("param2"), "value2")
        except Exception as exc:
            raise exc

    def test_plugin_csv_read(self):
        """ Test using csv plugin to read basic csv file """
        csv_url = self.get_asset_path("ds_test_1.csv")
        csv_plugin = self.get_csv_plugin(source={"url": csv_url})
        self.assertTrue(isinstance(csv_plugin, CsvDataframeSourcePlugin))
        self.assertEqual(csv_plugin.get_attribute("source.url"), csv_url)

        df = csv_plugin.run()
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 3)

    def test_plugin_code_dataframe_basic(self):
        """ Test using csv plugin to applies basic code to a dataframe """
        csv_url = self.get_asset_path("ds_test_1.csv")
        csv_plugin = self.get_csv_plugin(source={"url": csv_url})

        df = csv_plugin.run()
        self.assertEqual(df.loc[0, "First"], 10)

        # configure plugin to add 2 to all values in the first column of the dataframe
        code = "df['First'] = df['First'] + 2"
        plugin = self.factory.get_plugin(CODE_DATAFRAME_PLUGIN, code=code)

        # dataframe passed as POSITIONAL parameter
        df = plugin.run(df, action="dataset/process")
        self.assertEqual(df.loc[0, "First"], 12)

        # dataframe passed as POSITIONAL parameter
        df = plugin.run(df, action="dataset/process")
        self.assertEqual(df.loc[0, "First"], 14)

    def test_plugin_code_dataframe_bug(self):
        """ Test using csv plugin to applies code with a bug to a dataframe """
        csv_url = self.get_asset_path("ds_test_1.csv")
        csv_plugin = self.factory.get_plugin(CSV_DATAFRAME_SOURCE_PLUGIN, source={"url": csv_url})

        df = csv_plugin.run()
        self.assertEqual(df.loc[0, "First"], 10)

        # refers to df2 which DOES NOT exist
        code = "df['First'] = INTENTIONALLY_UNDEFINED_df2['First'] + 2"
        plugin = self.factory.get_plugin(CODE_DATAFRAME_PLUGIN, code=code)

        with self.assertRaises(PluginError):
            df = plugin.run(df, actions="dataset/process")

    def test_plugin_pipeline(self):
        """ Test grouping plugins into a multi step pipeline to retrieve and process a dataframe """
        pipeline_settings = {
            "type": PLUGIN_TYPE,
            "name": PIPELINE_PLUGIN,
            "plugins": [
                {
                    "type": PLUGIN_TYPE,
                    "name": CSV_DATAFRAME_SOURCE_PLUGIN,
                    "source": {"url": self.get_asset_path("ds_test_1.csv")},
                },
                {"type": PLUGIN_TYPE, "name": CODE_DATAFRAME_PLUGIN, "code": "df['First'] = df['First'] + 2"},
                {"type": PLUGIN_TYPE, "name": CODE_DATAFRAME_PLUGIN, "code": "df['First'] = df['First'] + 4"},
                {"type": PLUGIN_TYPE, "name": CODE_DATAFRAME_PLUGIN, "code": "df['First'] = df['First'] + 1"},
            ],
        }

        pipeline_plugin = self.factory.get_plugin(**pipeline_settings)
        self.assertTrue(isinstance(pipeline_plugin, PipelinePlugin))

        # call plugin chain; pass same random parameters just to see that they don't mess up things
        pipeline_df = pipeline_plugin.run("par1", "par2", mickey="mouse", minni="pluto")
        self.assertIsNotNone(pipeline_df)
        self.assertTrue(isinstance(pipeline_df, pd.DataFrame))

        # plugin chain increased first column by 2 + 4 + 1
        self.assertEqual(pipeline_df.loc[0, "First"], 17)
        self.assertEqual(pipeline_df.loc[1, "First"], 27)
        # second column untouched
        self.assertEqual(pipeline_df.loc[0, "Second"], 11)
        self.assertEqual(pipeline_df.loc[1, "Second"], 21)

        # call plugin chain again with some random positional
        # and named parameters just to see that they don't mess up things
        # parameters should be passed down the chain of plugins and ignored
        pipeline_df2 = pipeline_plugin.run("par1", "par2", mickey="mouse", minni="pluto")
        self.assertIsNotNone(pipeline_df2)
        self.assertTrue(isinstance(pipeline_df2, pd.DataFrame))

        # plugin chain increased first column by 2 + 4 + 1
        self.assertEqual(pipeline_df2.loc[0, "First"], 17)
        self.assertEqual(pipeline_df2.loc[1, "First"], 27)
        # second column untouched
        self.assertEqual(pipeline_df2.loc[0, "Second"], 11)
        self.assertEqual(pipeline_df2.loc[1, "Second"], 21)
