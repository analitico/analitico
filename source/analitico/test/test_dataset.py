import unittest
import json
import os
import os.path

import pandas as pd

import analitico.dataset
import analitico.utilities

from analitico.dataset import Dataset
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
        return Dataset(**json)

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

    