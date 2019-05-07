import unittest
import os.path
import pandas as pd
import random
import string
import io
import json

from analitico.factory import Factory
from analitico.schema import generate_schema

from .test_mixin import TestMixin

# pylint: disable=no-member

TITANIC_PUBLIC_URL = "https://storage.googleapis.com/public.analitico.ai/data/titanic/train.csv"


class FactoryTests(unittest.TestCase, TestMixin):
    """ Unit testing of Factory functionality: caching, creating items, plugins, etc """

    factory = Factory()

    def random_long_name(self):
        return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(512))

    def test_factory_get_cache_filename_repeatable(self):
        unique_id = self.random_long_name()
        file1_0 = self.factory.get_cache_filename(unique_id)
        for _ in range(0, 20):
            file1_1 = self.factory.get_cache_filename(unique_id)
            self.assertEqual(file1_0, file1_1)

    def test_factory_get_cache_filename_unique(self):
        file1 = self.factory.get_cache_filename(self.random_long_name())
        for _ in range(2, 20):
            file2 = self.factory.get_cache_filename(self.random_long_name())
            self.assertNotEqual(file1, file2)

    def test_factory_get_cache_filename_shared(self):
        unique_id = self.random_long_name()
        factory1 = Factory()
        file1_1 = factory1.get_cache_filename(unique_id)
        factory2 = Factory()
        file1_2 = factory2.get_cache_filename(unique_id)
        self.assertEqual(file1_1, file1_2)

    def test_factory_get_cache_filename_in_cache(self):
        unique_id = self.random_long_name()
        file1 = self.factory.get_cache_filename(unique_id)
        self.assertTrue(file1.startswith(self.factory.get_cache_directory()))
        self.assertEqual(os.path.dirname(file1), self.factory.get_cache_directory())

    def test_factory_get_url_stream(self):
        stream = self.factory.get_url_stream(TITANIC_PUBLIC_URL)
        df = pd.read_csv(stream)

        self.assertEqual(len(df), 891)
        self.assertEqual(df.columns[1], "Survived")
        self.assertEqual(df.loc[0, "Name"], "Braund, Mr. Owen òèéàù Harris")

    def test_factory_get_gzip_url_stream_(self):
        # Server sends API responses as gzip streams
        stream = self.factory.get_url_stream("https://analitico.ai/api/runtime")
        data = json.load(stream)["data"]
        self.assertTrue("hardware" in data)
        self.assertTrue("platform" in data)
        self.assertTrue("python" in data)
