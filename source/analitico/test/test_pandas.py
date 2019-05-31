import unittest
import tempfile
import numpy as np
import pytest

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from analitico.pandas import *


@pytest.mark.django_db
class PandasTests(unittest.TestCase):
    def get_random_dates_df(self):
        date_today = datetime.now()
        dates1 = pd.date_range(date_today, date_today + timedelta(21), freq="H")
        dates2 = pd.date_range(date_today, date_today + timedelta(21), freq="D")

        np.random.seed(seed=1111)
        data1 = np.random.randint(1, high=100, size=len(dates1))
        data2 = np.random.randint(1, high=100, size=len(dates1))
        data3 = np.random.randint(1, high=100, size=len(dates1))

        return pd.DataFrame({"Data1": data1, "Dates1": dates1, "Dates2": dates1, "Data2": data2, "Data3": data3})

    def test_pandas_augment_dates_all_columns(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1)

        self.assertIn("Dates1.dayofweek", df2.columns)
        self.assertIn("Dates1.year", df2.columns)
        self.assertIn("Dates1.month", df2.columns)
        self.assertIn("Dates1.day", df2.columns)
        self.assertIn("Dates1.hour", df2.columns)
        self.assertIn("Dates1.minute", df2.columns)
        self.assertNotIn("Dates1", df2.columns)

        self.assertIn("Dates2.dayofweek", df2.columns)
        self.assertIn("Dates2.year", df2.columns)
        self.assertIn("Dates2.month", df2.columns)
        self.assertIn("Dates2.day", df2.columns)
        self.assertIn("Dates2.hour", df2.columns)
        self.assertIn("Dates2.minute", df2.columns)
        self.assertNotIn("Dates2", df2.columns)

    def test_pandas_augment_dates_only_dates1(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates1")

        self.assertIn("Dates1.dayofweek", df2.columns)
        self.assertIn("Dates1.year", df2.columns)
        self.assertIn("Dates1.month", df2.columns)
        self.assertIn("Dates1.day", df2.columns)
        self.assertIn("Dates1.hour", df2.columns)
        self.assertIn("Dates1.minute", df2.columns)

        self.assertNotIn("Dates1", df2.columns)
        self.assertIn("Dates2", df2.columns)

    def test_pandas_augment_dates_only_dates2(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates2")

        self.assertIn("Dates2.dayofweek", df2.columns)
        self.assertIn("Dates2.year", df2.columns)
        self.assertIn("Dates2.month", df2.columns)
        self.assertIn("Dates2.day", df2.columns)
        self.assertIn("Dates2.hour", df2.columns)
        self.assertIn("Dates2.minute", df2.columns)

        self.assertNotIn("Dates2", df2.columns)
        self.assertIn("Dates1", df2.columns)

    def test_pandas_augment_dates_only_dayofweek(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates2", expand=["dayofweek"])

        self.assertIn("Dates2.dayofweek", df2.columns)
        self.assertNotIn("Dates2.year", df2.columns)
        self.assertNotIn("Dates2.month", df2.columns)
        self.assertNotIn("Dates2.day", df2.columns)
        self.assertNotIn("Dates2.hour", df2.columns)
        self.assertNotIn("Dates2.minute", df2.columns)

        self.assertNotIn("Dates2", df2.columns)
        self.assertIn("Dates1", df2.columns)

    def test_pandas_augment_dates_only_dayofweek_and_year(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates2", expand=["dayofweek", "year"])

        self.assertIn("Dates2.dayofweek", df2.columns)
        self.assertIn("Dates2.year", df2.columns)
        self.assertNotIn("Dates2.month", df2.columns)
        self.assertNotIn("Dates2.day", df2.columns)
        self.assertNotIn("Dates2.hour", df2.columns)
        self.assertNotIn("Dates2.minute", df2.columns)

        self.assertNotIn("Dates2", df2.columns)
        self.assertIn("Dates1", df2.columns)

    def test_pandas_augment_dates_check_position_2(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates2", expand=["dayofweek", "year"])

        cols = list(df2.columns)
        self.assertEqual(cols.index("Dates2.dayofweek"), 2)
        self.assertEqual(cols.index("Dates2.year"), 3)
        self.assertEqual(cols.index("Dates1"), 1)

    def test_pandas_augment_dates_check_position_1(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates1", expand=["dayofweek", "year"])

        cols = list(df2.columns)
        self.assertEqual(cols.index("Dates1.dayofweek"), 1)
        self.assertEqual(cols.index("Dates1.year"), 2)
        self.assertEqual(cols.index("Dates2"), 3)

    def test_pandas_augment_dates_check_position_no_drop(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates1", expand=["dayofweek", "year"], drop=False)

        cols = list(df2.columns)
        self.assertIn("Dates1", cols)
        self.assertEqual(cols.index("Dates1"), 1)
        self.assertEqual(cols.index("Dates1.dayofweek"), 2)
        self.assertEqual(cols.index("Dates1.year"), 3)
        self.assertEqual(cols.index("Dates2"), 4)

    def test_pandas_augment_dates_check_position_no_drop(self):
        df1 = self.get_random_dates_df()
        df1["Dates1"] = df1["Dates1"].astype("object")  # convert to strings
        self.assertEqual(df1["Dates1"].dtype, "object")

        df2 = augment_dates(df1, column="Dates1", expand=["dayofweek", "year"], drop=False)

        cols = list(df2.columns)
        self.assertIn("Dates1", cols)
        self.assertEqual(df1["Dates1"].dtype, "datetime64[ns]")
        self.assertNotEqual(df1["Dates1"].dtype, "object")
        self.assertEqual(cols.index("Dates1"), 1)
        self.assertEqual(cols.index("Dates1.dayofweek"), 2)
        self.assertEqual(cols.index("Dates1.year"), 3)
        self.assertEqual(cols.index("Dates2"), 4)

    def test_pandas_augment_dates_check_position_check_values(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates1", drop=False)

        # vector comparison
        dates = pd.DatetimeIndex(df2["Dates1"])
        self.assertTrue((dates.dayofweek == df2["Dates1.dayofweek"]).all())
        self.assertTrue((dates.year == df2["Dates1.year"]).all())
        self.assertTrue((dates.month == df2["Dates1.month"]).all())
        self.assertTrue((dates.day == df2["Dates1.day"]).all())
        self.assertTrue((dates.hour == df2["Dates1.hour"]).all())
        self.assertTrue((dates.minute == df2["Dates1.minute"]).all())

    def test_pandas_augment_dates_check_position_check_categoricals(self):
        df1 = self.get_random_dates_df()
        df2 = augment_dates(df1, column="Dates1")

        self.assertEqual(df2["Dates1.dayofweek"].dtype, "category")
        self.assertEqual(df2["Dates1.year"].dtype, "category")
        self.assertEqual(df2["Dates1.month"].dtype, "category")
        self.assertEqual(df2["Dates1.day"].dtype, "category")
        self.assertEqual(df2["Dates1.hour"].dtype, "category")
        self.assertEqual(df2["Dates1.minute"].dtype, "category")
