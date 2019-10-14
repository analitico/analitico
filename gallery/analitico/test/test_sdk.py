import unittest
import os.path
import pandas as pd
import datetime
import tempfile

import analitico

from analitico import logger, AnaliticoException
from analitico.utilities import id_generator, time_ms
from analitico.models import Item, Dataset, Recipe, Notebook

from .test_mixin import TestMixin

# pylint: disable=no-member

ANALITICO_TEST_TOKEN = os.environ["ANALITICO_TEST_TOKEN"]
ANALITICO_TEST_WORKSPACE_ID = os.environ["ANALITICO_TEST_WORKSPACE_ID"]

TITANIC_PUBLIC_URL = "https://storage.googleapis.com/public.analitico.ai/data/titanic/train.csv"

MB_SIZE = 1024 * 1024


class SDKTests(unittest.TestCase, TestMixin):
    """ Testing of Factory/sdk functionality: caching, creating items, plugins, etc """

    # Create a factory/sdk with out test token that can
    # access our test workspace in read and write model
    sdk = analitico.authorize_sdk(
        token=ANALITICO_TEST_TOKEN,
        workspace_id=ANALITICO_TEST_WORKSPACE_ID,
        endpoint="https://staging.analitico.ai/api/",
    )

    def setUp(self):
        if not (ANALITICO_TEST_TOKEN and ANALITICO_TEST_WORKSPACE_ID):
            msg = "The enviroment variable ANALITICO_TEST_TOKEN and ANALITICO_TEST_WORKSPACE_ID should be set to run this test."
            raise AnaliticoException(msg)

    ##
    ## Utility methods
    ##

    def upload_random_rainbows(self, item: Item, size: int):
        """ Uploads random bytes to test upload limits, timeouts, etc. Size of upload is specified by caller. """
        try:
            # random directory to test subdirectory generation
            remotepath = f"tst_dir_{id_generator(12)}/abc/def/ghi/unicorns.data"
            logger.info(f"\nsdk upload {remotepath}")

            # random bytes to avoid compression, etc
            data1 = bytearray(os.urandom(size))

            # upload data directly to item's storage
            with tempfile.NamedTemporaryFile() as f1:
                f1.write(data1)
                started_ms = time_ms()
                item.upload(filepath=f1.name, remotepath=remotepath, direct=True)

                elapsed_ms = max(1, time_ms(started_ms))
                kb_sec = (size / 1024.0) / (elapsed_ms / 1000.0)
                msg = f"sdk upload (direct): {size / MB_SIZE} MB in {elapsed_ms} ms, {kb_sec:.0f} KB/s"
                logger.info(msg)

            # download (streaming)
            started_ms = time_ms()
            stream2 = item.download(remotepath, stream=True)
            with tempfile.NamedTemporaryFile() as f2:
                for chunk in iter(stream2):
                    f2.write(chunk)

                elapsed_ms = max(1, time_ms(started_ms))
                kb_sec = (size / 1024.0) / (elapsed_ms / 1000.0)
                msg = f"sdk download (streaming): {size / MB_SIZE} MB in {elapsed_ms} ms, {kb_sec:.0f} KB/s"
                logger.info(msg)

                f2.seek(0)
                data2 = f2.file.read()
                self.assertEqual(data1, data2)

            # upload data to /files APIs
            with tempfile.NamedTemporaryFile() as f1:
                f1.write(data1)
                started_ms = time_ms()
                item.upload(filepath=f1.name, remotepath=remotepath, direct=False)

                elapsed_ms = max(1, time_ms(started_ms))
                kb_sec = (size / 1024.0) / (elapsed_ms / 1000.0)
                msg = f"sdk upload (server): {size / MB_SIZE} MB in {elapsed_ms} ms, {kb_sec:.0f} KB/s"
                logger.info(msg)

            # download data from item's storage
            with tempfile.NamedTemporaryFile() as f3:
                started_ms = time_ms()
                item.download(remotepath, f3.name)
                elapsed_ms = max(1, time_ms(started_ms))
                kb_sec = (size / 1024.0) / (elapsed_ms / 1000.0)
                msg = f"sdk download (file): {size / MB_SIZE} MB in {elapsed_ms} ms, {kb_sec:.0f} KB/s"
                logger.info(msg)

                data3 = f3.file.read()
                self.assertEqual(data1, data3)

        except Exception:
            raise

        finally:
            pass

    ##
    ## get
    ##

    def test_sdk_get_item(self):
        item = self.sdk.get_item("rx_ho374b88")

        self.assertIsNotNone(item)
        self.assertIsInstance(item, analitico.Recipe)
        self.assertTrue(item.id.startswith(analitico.RECIPE_PREFIX))
        self.assertEqual(item.type, "recipe")

    def test_sdk_get_recipe(self):
        recipe = self.sdk.get_recipe("rx_ho374b88")

        self.assertIsNotNone(recipe)
        self.assertIsInstance(recipe, analitico.Recipe)
        self.assertTrue(recipe.id.startswith(analitico.RECIPE_PREFIX))
        self.assertEqual(recipe.type, "recipe")

        recipe_str = str(recipe)
        self.assertEqual(recipe_str, "recipe: rx_ho374b88")

    ##
    ## create
    ##

    def test_sdk_create_item(self):
        item = None
        try:
            item = self.sdk.create_item(analitico.DATASET_TYPE)
            self.assertIsNotNone(item)
            self.assertIsInstance(item, analitico.Dataset)
            self.assertTrue(item.id.startswith(analitico.DATASET_PREFIX))
            self.assertEqual(item.type, "dataset")
        finally:
            if item:
                item.delete()

    def test_sdk_create_item_with_title(self):
        item = None
        try:
            title = "Testing at " + datetime.datetime.utcnow().isoformat()
            item = self.sdk.create_item(analitico.DATASET_TYPE, title=title)
            self.assertEqual(item.get_attribute("title"), title)
            self.assertEqual(item.title, title)
        finally:
            if item:
                item.delete()

    ##
    ## save
    ##

    def test_sdk_save_item_with_updates(self):
        item = None
        try:
            title = "Testing at " + datetime.datetime.utcnow().isoformat()
            item = self.sdk.create_item(analitico.DATASET_TYPE, title=title)
            self.assertEqual(item.get_attribute("title"), title)
            self.assertEqual(item.title, title)

            # update title, save updates on service
            title_v2 = title + " v2"
            item.title = title_v2
            item.save()
            self.assertEqual(item.get_attribute("title"), title_v2)
            self.assertEqual(item.title, title_v2)

            # retrieve new object from service
            item_again = self.sdk.get_item(item.id)
            self.assertEqual(item_again.get_attribute("title"), title_v2)
            self.assertEqual(item_again.title, title_v2)

        finally:
            if item:
                item.delete()

    ##
    ## upload
    ##

    def test_sdk_upload_dataframe(self):
        dataset = None
        try:
            title = "Boston test at " + datetime.datetime.utcnow().isoformat()
            dataset = self.sdk.create_item(analitico.DATASET_TYPE, title=title)

            # import is here to avoid importing the dependency unless run
            from sklearn.datasets import load_boston

            # upload boston dataframe to service
            boston_dataset = load_boston()
            boston_df1 = pd.DataFrame(boston_dataset.data, columns=boston_dataset.feature_names)
            dataset.upload(df=boston_df1, remotepath="boston.parquet")

            # download boston dataframe from service
            boston_df2 = dataset.download("boston.parquet", df=True)
            self.assertEqual(len(boston_df1.index), len(boston_df2.index))
            self.assertTrue(pd.DataFrame.equals(boston_df1, boston_df2))

        finally:
            if dataset:
                dataset.delete()

    def test_sdk_upload_download_8mb(self):
        dataset = None
        try:
            dataset = self.sdk.create_item(analitico.DATASET_TYPE, title="Upload 8 MB")
            self.upload_random_rainbows(dataset, 8 * MB_SIZE)
        finally:
            if dataset:
                dataset.delete()

    def test_sdk_upload_download_64mb(self):
        dataset = None
        try:
            dataset = self.sdk.create_item(analitico.DATASET_TYPE, title="Upload 64 MB")
            self.upload_random_rainbows(dataset, 64 * MB_SIZE)
        finally:
            if dataset:
                dataset.delete()

    # slowing down CD/CI pipeline, this test is run manually
    def OFFtest_sdk_upload_download_1gb(self):
        dataset = None
        try:
            dataset = self.sdk.create_item(analitico.DATASET_TYPE, title="Upload 1 GB")
            self.upload_random_rainbows(dataset, 1024 * MB_SIZE)
        finally:
            if dataset:
                dataset.delete()

    # slowing down CD/CI pipeline, this test is run manually
    def OFFtest_sdk_upload_download_4gb(self):
        dataset = None
        try:
            dataset = self.sdk.create_item(analitico.DATASET_TYPE, title="Upload 4 GB")
            self.upload_random_rainbows(dataset, 4096 * MB_SIZE)
        finally:
            if dataset:
                dataset.delete()
