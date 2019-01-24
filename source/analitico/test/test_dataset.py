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

# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + '/assets'

class DatasetTests(unittest.TestCase):
    """ Unit testing of Dataset functionality, reading, converting, transforms, saving, etc """

    ## Utilities

    def read_json_asset(self, path):
        abs_path = os.path.join(ASSETS_PATH, path)
        with open(abs_path, 'r') as f:
            text = f.read()
            text = text.replace('{assets}', ASSETS_PATH)
            return json.loads(text)

    def read_dataset_asset(self, path):
        json = self.read_json_asset(path)
        return ds_factory(**json)

    def read_dataframe_asset(self, path):
        ds = self.read_dataset_asset(path)
        return ds.get_dataframe()

    ## Test creations

    def test_dataset_csv1_basics(self):
        """ Test empty dataset creation """
        try:
            ds = self.read_dataset_asset('ds_test_1.json')
            self.assertEqual(ds.id, 'ds_1')

            df = ds.get_dataframe()
            self.assertTrue(type(df) is pd.DataFrame)
            self.assertEqual(len(df), 3)
            self.assertEqual(df.columns[0], 'First')
            self.assertEqual(df.columns[1], 'Second')
            self.assertEqual(df.columns[2], 'Third')
            self.assertEqual(df.iloc[0,0], 10)
            self.assertEqual(df.iloc[1,1], 21)
            self.assertEqual(df.iloc[2,2], 32)
        except Exception as exc:
            raise exc


    def test_dataset_csv2_types_default(self):
        """ Test standard data type conversions """
        try:
            ds = self.read_dataset_asset('ds_test_2.json')
            self.assertEqual(ds.id, 'ds_2')

            df = ds.get_dataframe()
            self.assertEqual(df.dtypes[0], 'int64')
            self.assertEqual(df.dtypes[1], 'O')
            self.assertEqual(df.dtypes[2], 'float64')
        except Exception as exc:
            raise exc


    def test_dataset_csv3_types_cast_float(self):
        """ Test forcing integers to be floating point instead """
        try:
            df = self.read_dataframe_asset('ds_test_3_cast_float.json')
            self.assertEqual(df.dtypes[0], 'float64') # would normally be int, but was forced to float
            self.assertEqual(df.dtypes[1], 'O')
            self.assertEqual(df.dtypes[2], 'float64')
        except Exception as exc:
            raise exc


    def test_dataset_csv3_types_cast_string(self):
        """ Test forcing float column to string """
        try:
            df = self.read_dataframe_asset('ds_test_3_cast_string.json')
            self.assertEqual(df.dtypes[0], 'int64')
            self.assertEqual(df.dtypes[1], 'O')
            self.assertEqual(df.dtypes[2], 'O') # third column would be float, but is cast to string
            self.assertEqual(df.iloc[2,2], '32.50')
        except Exception as exc:
            raise exc


    def test_dataset_csv4_types_datetime_is8601(self):
        """ Test reading datetime in ISO8601 format """
        try:
            df = self.read_dataframe_asset('ds_test_4.json')
            self.assertEqual(df.dtypes[0], 'int64')
            self.assertEqual(df.dtypes[1], 'O')

            self.assertTrue(type(df.iloc[0,2]) is pd.Timestamp)
            self.assertTrue(type(df.iloc[1,2]) is pd.Timestamp)
            self.assertTrue(type(df.iloc[2,2]) is pd.Timestamp)
            self.assertTrue(type(df.iloc[3,2]) is pd.Timestamp)

            self.assertEqual(df.iloc[0,2], pd.Timestamp('2019-01-20 00:00:00'))
            self.assertEqual(df.iloc[1,2], pd.Timestamp('2019-01-20 16:30:15'))
            self.assertEqual(df.iloc[2,2], pd.Timestamp('2019-02-01 00:00:00'))
            self.assertEqual(df.iloc[3,2], pd.Timestamp('2019-01-01 00:00:00'))

            # Timezones are state machines from row to row...
            self.assertEqual(df.iloc[4,2], pd.Timestamp('2019-09-15 15:53:00')) # 2019-09-15T15:53:00
            self.assertEqual(df.iloc[5,2], pd.Timestamp('2019-09-15 10:53:00')) # 2019-09-15T15:53:00+05:00 (changes timezone)
            self.assertEqual(df.iloc[6,2], pd.Timestamp('2019-09-15 10:53:00')) # 2019-09-15T15:53:00 (maintains +5 timezone)
            self.assertEqual(df.iloc[7,2], pd.Timestamp('2019-09-15 15:53:00')) # 2019-09-15T15:53:00+00 (reverts timezone)
            self.assertEqual(df.iloc[8,2], pd.Timestamp('2019-09-15 17:23:00')) # 2019-09-15T15:53:00-01:30 (changes timezone)
            self.assertEqual(df.iloc[9,2], pd.Timestamp('2008-09-15 15:53:00')) # 20080915T155300Z (zulu time)

            # Time only uses today's date
            self.assertEqual(df.iloc[10,2], pd.Timestamp('15:53:00.322348'))    # 15:53:00.322348
        
            # Examples:
            # http://support.sas.com/documentation/cdl/en/lrdict/64316/HTML/default/viewer.htm#a003169814.htm
        except Exception as exc:
            raise exc
