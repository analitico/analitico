import os
import os.path
import numpy as np
import pandas as pd
import tempfile
import random
import string
import pytest
import sklearn
import sklearn.datasets
import urllib.parse

from django.test import tag
from django.urls import reverse

from rest_framework import status
from analitico.utilities import time_ms

import analitico
import analitico.plugin

from analitico import logger
from analitico.pandas import pd_read_csv
from .utils import AnaliticoApiTestCase, ASSETS_PATH
from api.pagination import MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member
# pylint: disable=unused-variable

# we test and try files using these formats
TEST_DATA_SUFFIXES = (".csv", ".parquet")

# TODO find parquet's real mime type
PARQUET_MIME_TYPE = "application/octet-stream"


@pytest.mark.django_db
class DatasetTests(AnaliticoApiTestCase):
    """ Test datasets operations like uploading assets, processing pipelines, downloading data, etc """

    def upload_titanic_csv(self, dataset_id="ds_titanic_1", asset_name="titanic_1.csv"):
        url = reverse("api:dataset-files", args=(dataset_id, asset_name))
        response = self.upload_file(url, asset_name, "text/csv", token=self.token1)
        return url, response

    def upload_dataset(self, dataset="boston", suffix=".csv"):
        # https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_wine.html

        df = None
        filename = os.path.join(ASSETS_PATH, dataset + suffix)
        if dataset == "boston":
            data = sklearn.datasets.load_boston()
        elif dataset == "wine":
            data = sklearn.datasets.load_wine()
        elif dataset == "iris":
            data = sklearn.datasets.load_iris()
        elif dataset == "nba":
            asset = os.path.join(ASSETS_PATH, "nba.csv")
            df = pd_read_csv(asset)

        if df is None:
            # np.c_ is the numpy concatenate function
            d1 = np.c_[data["data"], data["target"]]
            d2 = list(data["feature_names"])
            d2.append("target")
            df = pd.DataFrame(data=d1, columns=d2)

        mimetype = "application/octet-stream"
        if suffix == ".csv":
            df.to_csv(filename, index=False)  # no index column!
            mimetype = "text/csv"
        elif suffix == ".parquet":
            df.to_parquet(filename)
            mimetype = PARQUET_MIME_TYPE
        else:
            raise NotImplementedError(f"{suffix} format is not supported")
        url = reverse("api:dataset-files", args=("ds_sklearn", f"{dataset}{suffix}"))
        self.upload_file(url, filename, mimetype, token=self.token1)
        return url

    def upload_large_random_data(self, dataset_id, N=10000, k=5, suffix=".csv"):
        df = pd.DataFrame(
            {
                "Number": range(0, N, 1),
                "Random": np.random.randint(k, k + 100, size=N),
                "String": pd.Series(random.choice(string.ascii_uppercase) for _ in range(N)),
            }
        )
        url = reverse("api:dataset-files", args=(dataset_id, f"data{suffix}"))
        with tempfile.NamedTemporaryFile(suffix=suffix) as f:
            if suffix == ".csv":
                df.to_csv(f.name)
                self.upload_file(url, f.name, "text/csv", token=self.token1)
            if suffix == ".parquet":
                df.to_parquet(f.name)
                self.upload_file(url, f.name, PARQUET_MIME_TYPE, token=self.token1)
        return url

    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:workspace-list")
            self.upload_items(url, analitico.WORKSPACE_PREFIX)
            url = reverse("api:dataset-list")
            self.upload_items(url, analitico.DATASET_PREFIX)
        except Exception as exc:
            print(exc)
            raise exc

    def test_dataset_get_titanic(self):
        item = self.get_item("dataset", "ds_titanic_1", self.token1)
        self.assertEqual(item["id"], "ds_titanic_1")
        self.assertEqual(item["attributes"]["title"], "Kaggle - Titanic training dataset (train.csv)")
        self.assertEqual(item["attributes"]["description"], "https://www.kaggle.com/c/titanic")

    def test_dataset_csv_get_titanic_upload_csv_check_metadata(self):
        # no assets before uploading
        ds_url = reverse("api:dataset-detail", args=("ds_titanic_1",))
        ds_response = self.client.get(ds_url, format="json")
        ds_data1 = ds_response.data
        self.assertTrue("assets" not in ds_data1["attributes"])

        # upload titanic_1.csv
        self.upload_titanic_csv("ds_titanic_1")

        # check dataset again, this time should have csv asset
        ds_url = reverse("api:dataset-files", args=("ds_titanic_1", "titanic_1.csv")) + "?metadata=true"
        ds_response = self.client.get(ds_url)
        ds_data = ds_response.data
        self.assertEqual(len(ds_data), 1)
        self.assertEqual(ds_data[0]["id"], "/titanic_1.csv")
        self.assertEqual(ds_data[0]["attributes"]["content_type"], "text/csv")
        self.assertEqual(ds_data[0]["attributes"]["size"], 61216)

    def test_dataset_upload_boston_check_metadata(self):
        for suffix in TEST_DATA_SUFFIXES:
            # upload boston.suffix
            url = self.upload_dataset(dataset="boston", suffix=suffix)

            # check asset again, should have only basic file metadata
            response = self.client.get(url + "?metadata=true")
            self.assertEqual(len(response.data), 1)
            data = response.data[0]
            self.assertEqual(data["id"], f"/boston{suffix}")
            self.assertTrue("metadata" not in data["attributes"])
            if suffix == ".csv":
                self.assertEqual(data["attributes"]["content_type"], "text/csv")
                self.assertEqual(data["attributes"]["size"], 39171)
            if suffix == ".parquet":
                # TODO why parquet file doesn't have the generic mime?
                self.assertEqual(data["attributes"]["content_type"], None)
                # NOTE you cannot rely on data size being the same of different platforms
                # self.assertEqual(data["attributes"]["size"], 27957)

            # check asset again, this time with fresh metadata obtain from reading the file
            response = self.client.get(url + "?metadata=true&refresh=true")
            data = response.data[0]
            self.assertEqual(data["id"], f"/boston{suffix}")
            self.assertIsNotNone(data["attributes"]["metadata"])
            metadata = data["attributes"]["metadata"]
            self.assertEqual(int(metadata["total_records"]), 506)

            columns = metadata["schema"]["columns"]
            self.assertEqual(len(columns), 14)
            self.assertEqual(columns[0]["name"], "CRIM")
            self.assertEqual(columns[0]["type"], "float")
            self.assertEqual(columns[1]["name"], "ZN")
            self.assertEqual(columns[1]["type"], "float")

    def test_dataset_upload_wine_check_metadata(self):
        for suffix in TEST_DATA_SUFFIXES:
            # upload wine.suffix
            url = self.upload_dataset(dataset="wine", suffix=suffix)

            # check asset again, should have only basic file metadata
            response = self.client.get(url + "?metadata=true")
            self.assertEqual(len(response.data), 1)
            data = response.data[0]
            self.assertEqual(data["id"], f"/wine{suffix}")
            self.assertTrue("metadata" not in data["attributes"])
            if suffix == ".csv":
                self.assertEqual(data["attributes"]["content_type"], "text/csv")
                self.assertEqual(data["attributes"]["size"], 12617)
            if suffix == ".parquet":
                # TODO why parquet file doesn't have the generic mime?
                self.assertEqual(data["attributes"]["content_type"], None)
                # NOTE you cannot rely on data size being the same of different platforms
                # self.assertEqual(data["attributes"]["size"], 14190)

            # check asset again, this time with fresh metadata obtain from reading the file
            response = self.client.get(url + "?metadata=true&refresh=true")
            data = response.data[0]
            self.assertEqual(data["id"], f"/wine{suffix}")
            self.assertIsNotNone(data["attributes"]["metadata"])
            metadata = data["attributes"]["metadata"]
            self.assertEqual(int(metadata["total_records"]), 178)

            columns = metadata["schema"]["columns"]
            self.assertEqual(len(columns), 14)
            self.assertEqual(columns[0]["name"], "alcohol")
            self.assertEqual(columns[0]["type"], "float")
            self.assertEqual(columns[1]["name"], "malic_acid")
            self.assertEqual(columns[1]["type"], "float")

    def test_dataset_upload_iris_check_metadata(self):
        for suffix in TEST_DATA_SUFFIXES:
            # upload iris.suffix
            url = self.upload_dataset(dataset="iris", suffix=suffix)

            # check asset again, should have only basic file metadata
            response = self.client.get(url + "?metadata=true")
            self.assertEqual(len(response.data), 1)
            data = response.data[0]
            self.assertEqual(data["id"], f"/iris{suffix}")
            self.assertTrue("metadata" not in data["attributes"])
            if suffix == ".csv":
                self.assertEqual(data["attributes"]["content_type"], "text/csv")
                self.assertEqual(data["attributes"]["size"], 3077)
            if suffix == ".parquet":
                # TODO why parquet file doesn't have the generic mime?
                self.assertEqual(data["attributes"]["content_type"], None)
                # NOTE you cannot rely on data size being the same of different platforms
                self.assertEqual(data["attributes"]["size"], 3482)

            # check asset again, this time with fresh metadata obtained from reading the file
            response = self.client.get(url + "?metadata=true&refresh=true")
            data = response.data[0]
            self.assertEqual(data["id"], f"/iris{suffix}")
            self.assertIsNotNone(data["attributes"]["metadata"])
            metadata = data["attributes"]["metadata"]
            self.assertEqual(int(metadata["total_records"]), 150)

            columns = metadata["schema"]["columns"]
            self.assertEqual(len(columns), 5)
            self.assertEqual(columns[0]["name"], "sepal length (cm)")
            self.assertEqual(columns[0]["type"], "float")
            self.assertEqual(columns[1]["name"], "sepal width (cm)")
            self.assertEqual(columns[1]["type"], "float")

    def test_dataset_upload_nba_check_metadata(self):
        for suffix in TEST_DATA_SUFFIXES:
            # upload nba.suffix
            url = self.upload_dataset(dataset="nba", suffix=suffix)

            # check asset again, should have only basic file metadata
            response = self.client.get(url + "?metadata=true")
            self.assertEqual(len(response.data), 1)
            data = response.data[0]
            self.assertEqual(data["id"], f"/nba{suffix}")
            self.assertTrue("metadata" not in data["attributes"])
            if suffix == ".csv":
                self.assertEqual(data["attributes"]["content_type"], "text/csv")
                self.assertEqual(data["attributes"]["size"], 32814)
            if suffix == ".parquet":
                # TODO why parquet file doesn't have the generic mime?
                self.assertEqual(data["attributes"]["content_type"], None)
                # NOTE you cannot rely on data size being the same of different platforms
                # self.assertEqual(data["attributes"]["size"], 16785)

            # check asset again, this time with fresh metadata obtain from reading the file
            response = self.client.get(url + "?metadata=true&refresh=true")
            data = response.data[0]
            self.assertEqual(data["id"], f"/nba{suffix}")
            self.assertIsNotNone(data["attributes"]["metadata"])
            metadata = data["attributes"]["metadata"]
            self.assertEqual(int(metadata["total_records"]), 457)

            columns = metadata["schema"]["columns"]
            self.assertEqual(len(columns), 9)
            self.assertEqual(columns[0]["name"], "Name")
            self.assertEqual(columns[0]["type"], "string")
            self.assertEqual(columns[4]["name"], "Age")
            self.assertEqual(columns[4]["type"], "float")

    def test_dataset_csv_upload_get_info(self):
        # upload and process titanic_1.csv
        url, _ = self.upload_titanic_csv("ds_titanic_4")

        # request information on data, should not have metadata yet
        response = self.client.get(url + "?metadata=true")
        self.assertStatusCode(response)
        self.assertFalse(response.streaming)
        data = response.data[0]
        self.assertNotIn("metadata", data["attributes"])

        # request information on data, check schema is present, if not create it
        response = self.client.get(url + "?metadata=true&refresh=true")
        self.assertStatusCode(response)
        self.assertFalse(response.streaming)
        data = response.data[0]
        self.assertIn("metadata", data["attributes"])
        metadata = data["attributes"]["metadata"]
        self.assertEqual(len(metadata["schema"]["columns"]), 12)

    ##
    ## Paging tabular data files (eg: csv, parquet) as json
    ##

    def test_dataset_paging_no_parameters(self):
        for suffix in TEST_DATA_SUFFIXES:
            N = 500
            url = self.upload_large_random_data("ds_titanic_4", N, suffix=suffix) + "?records=true"
            response = self.client.get(url)
            self.assertStatusCode(response)

            records = response.data["data"]
            self.assertEqual(len(records), 25)
            self.assertEqual(records[0]["Number"], 0)
            self.assertEqual(records[24]["Number"], 24)
            self.assertTrue("meta" in response.data)
            self.assertEqual(response.data["meta"]["page"], 0)
            self.assertEqual(response.data["meta"]["page_size"], DEFAULT_PAGE_SIZE)
            self.assertEqual(response.data["meta"]["page_records"], DEFAULT_PAGE_SIZE)
            self.assertEqual(response.data["meta"]["total_pages"], N / DEFAULT_PAGE_SIZE)
            self.assertEqual(response.data["meta"]["total_records"], N)

    def test_dataset_paging_no_parameters_uneven_pages(self):
        for suffix in TEST_DATA_SUFFIXES:
            N = 496  # last page is different
            url = self.upload_large_random_data("ds_titanic_4", N, suffix=suffix) + "?records=true"
            response = self.client.get(url)
            self.assertStatusCode(response)

            records = response.data["data"]
            self.assertEqual(len(records), DEFAULT_PAGE_SIZE)
            self.assertEqual(records[0]["Number"], 0)
            self.assertEqual(records[N % DEFAULT_PAGE_SIZE]["Number"], N % DEFAULT_PAGE_SIZE)
            # metadata
            meta = response.data["meta"]
            self.assertEqual(meta["page"], 0)
            self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
            self.assertEqual(meta["total_pages"], int((N + DEFAULT_PAGE_SIZE - 1) / DEFAULT_PAGE_SIZE))
            self.assertEqual(meta["total_records"], N)

    def test_dataset_paging_no_parameters_first_page(self):
        for suffix in TEST_DATA_SUFFIXES:
            N = DEFAULT_PAGE_SIZE * 20
            url = self.upload_large_random_data("ds_titanic_4", N, suffix=suffix)
            response = self.client.get(url + "?records=true")
            self.assertStatusCode(response)

            records = response.data["data"]
            self.assertEqual(len(records), DEFAULT_PAGE_SIZE)
            self.assertEqual(records[0]["Number"], 0)
            self.assertEqual(records[DEFAULT_PAGE_SIZE - 1]["Number"], DEFAULT_PAGE_SIZE - 1)
            meta = response.data["meta"]
            self.assertEqual(meta["page"], 0)
            self.assertEqual(meta["page_records"], DEFAULT_PAGE_SIZE)
            self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
            self.assertEqual(meta["total_records"], N)

    def test_dataset_paging_second_page(self):
        for suffix in TEST_DATA_SUFFIXES:
            N = DEFAULT_PAGE_SIZE * 40
            url = self.upload_large_random_data("ds_titanic_4", N, suffix=suffix) + "?records=true&page=2"
            response = self.client.get(url)
            self.assertStatusCode(response)

            records = response.data["data"]
            self.assertEqual(len(records), DEFAULT_PAGE_SIZE)
            self.assertEqual(records[0]["Number"], DEFAULT_PAGE_SIZE * 2)
            self.assertEqual(records[DEFAULT_PAGE_SIZE - 1]["Number"], (DEFAULT_PAGE_SIZE * 3) - 1)

    def test_dataset_paging_last_page(self):
        for suffix in TEST_DATA_SUFFIXES:
            N = (DEFAULT_PAGE_SIZE * 20) - 10
            url = self.upload_large_random_data("ds_titanic_4", N, suffix=suffix) + "?records=true&page=19"
            response = self.client.get(url)
            self.assertStatusCode(response)

            records = response.data["data"]
            self.assertEqual(len(records), N % DEFAULT_PAGE_SIZE)
            self.assertEqual(records[0]["Number"], DEFAULT_PAGE_SIZE * 19)
            self.assertEqual(records[(N % DEFAULT_PAGE_SIZE) - 1]["Number"], N - 1)
            meta = response.data["meta"]
            self.assertEqual(meta["page"], 19)
            self.assertEqual(meta["page_records"], N % DEFAULT_PAGE_SIZE)
            self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
            self.assertEqual(meta["total_records"], N)
            self.assertEqual(meta["total_pages"], int((N + DEFAULT_PAGE_SIZE - 1) / DEFAULT_PAGE_SIZE))

    def test_dataset_paging_beyond_last_page(self):
        for suffix in TEST_DATA_SUFFIXES:
            N = (DEFAULT_PAGE_SIZE * 20) - 10
            url = self.upload_large_random_data("ds_titanic_4", N, suffix=suffix)
            response = self.client.get(url + "?records=true&page=20")
            self.assertStatusCode(response)

            records = response.data["data"]
            self.assertEqual(len(records), 0)
            meta = response.data["meta"]
            self.assertEqual(meta["page"], 20)
            self.assertEqual(meta["page_records"], 0)
            self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
            self.assertEqual(meta["total_records"], N)
            self.assertEqual(meta["total_pages"], 20)

            # beyond last
            response = self.client.get(url + "?records=true&page=310")
            self.assertStatusCode(response)
            records = response.data["data"]
            self.assertEqual(len(records), 0)
            meta = response.data["meta"]
            self.assertEqual(meta["page"], 310)
            self.assertEqual(meta["page_records"], 0)
            self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
            self.assertEqual(meta["total_records"], N)
            self.assertEqual(meta["total_pages"], 20)

    @tag("slow", "live")
    def test_dataset_paging_scan_pages_check_performance(self):
        for suffix in TEST_DATA_SUFFIXES:
            N = DEFAULT_PAGE_SIZE * 5000  # large but not huge 125K records
            url = self.upload_large_random_data("ds_titanic_4", N, suffix=suffix)

            # first page loading time may be higher because cache is cold
            response = self.client.get(url + "?records=true")
            self.assertStatusCode(response)
            records = response.data["data"]
            self.assertEqual(len(records), DEFAULT_PAGE_SIZE)

            # WARNING: THIS TEST CHECKS PERFORMANCE AND WILL THROW IF THE LOOP IS SLOW
            # THIS MEANS THAT IF YOU SETUP A BREAKPOINT AND DEBUG THE CODE YOU WILL GET AN ASSERT
            total_ms = time_ms()
            for i in range(1, 50):  # 50 runs
                page_number = random.randint(1, 3000)  # random page
                loading_ms = time_ms()
                response = self.client.get(url + f"?records=true&page={page_number}")
                self.assertStatusCode(response)
                records = response.data["data"]
                self.assertEqual(len(records), DEFAULT_PAGE_SIZE)
                self.assertEqual(records[0]["Number"], page_number * DEFAULT_PAGE_SIZE)
                self.assertEqual(records[DEFAULT_PAGE_SIZE - 1]["Number"], ((page_number + 1) * DEFAULT_PAGE_SIZE) - 1)
                loading_ms = time_ms(loading_ms)
                self.assertLess(int(loading_ms), 100, "Page loading time should be under 100ms")
            total_ms = time_ms(total_ms)
            average_ms = float(total_ms) / 40
            self.assertLess(int(loading_ms), 150, "Average page loading time should be less than 150ms")
            logger.info("Average page loading time for %s is %d ms", suffix, average_ms)

    def test_dataset_paging_larger_page(self):
        for suffix in TEST_DATA_SUFFIXES:
            url = self.upload_large_random_data("ds_titanic_4", 1000, suffix=suffix)
            response = self.client.get(url + "?records=true&page=10&page_size=50")
            self.assertStatusCode(response)

            records = response.data["data"]
            self.assertEqual(len(records), 50)
            self.assertEqual(records[0]["Number"], 500)
            self.assertEqual(records[49]["Number"], 549)
            meta = response.data["meta"]
            self.assertEqual(meta["page"], 10)
            self.assertEqual(meta["page_size"], 50)

    def test_dataset_paging_huge_page(self):
        for suffix in TEST_DATA_SUFFIXES:
            N = MAX_PAGE_SIZE * 20
            url = self.upload_large_random_data("ds_titanic_4", N, suffix=suffix)
            response = self.client.get(url + "?records=true&page=10&page_size=500")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            records = response.data["data"]
            self.assertEqual(len(records), MAX_PAGE_SIZE)
            self.assertEqual(records[0]["Number"], MAX_PAGE_SIZE * 10)  # constrained to max_page_size
            meta = response.data["meta"]
            self.assertEqual(meta["page"], 10)
            self.assertEqual(meta["page_size"], MAX_PAGE_SIZE)

    ##
    ## Filtering data ?query=
    ##

    def get_filtered_nba(self, query=None, sort=None, suffix=None, params=None, status_code=None):
        url = self.upload_dataset(dataset="nba", suffix=suffix) + "?records=true"
        if query:
            url += "&query=" + urllib.parse.quote(query)
        if sort:
            url += "&order=" + urllib.parse.quote(sort)
        if params:
            url += "&" + params
        response = self.client.get(url)
        if status_code:
            self.assertEqual(response.status_code, status_code)
            return response

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["data"]

    @tag("query")
    def test_dataset_filtering_single(self):
        for suffix in TEST_DATA_SUFFIXES:
            records = self.get_filtered_nba("College == 'Arizona'", suffix=suffix, params="page_size=1000")
            self.assertEqual(len(records), 13)
            self.assertEqual(records[0]["Name"], "Rondae Hollis-Jefferson")

    @tag("query")
    def test_dataset_filtering_double(self):
        for suffix in TEST_DATA_SUFFIXES:
            records = self.get_filtered_nba("Age < 25 and College == 'Arizona'", suffix=suffix, params="page_size=1000")
            self.assertEqual(len(records), 4)
            self.assertEqual(records[0]["Name"], "Rondae Hollis-Jefferson")

    @tag("query")
    def test_dataset_filtering_paged(self):
        for suffix in TEST_DATA_SUFFIXES:
            # obtain first 100 records (page size is limited to max page in any case)
            records1 = self.get_filtered_nba("Position == 'SG'", suffix=suffix, params="page_size=1000")
            self.assertEqual(len(records1), 100)
            self.assertEqual(records1[0]["Name"], "John Holland")

            records2 = self.get_filtered_nba("Position == 'SG'", suffix=suffix)
            self.assertEqual(len(records2), DEFAULT_PAGE_SIZE)
            self.assertEqual(records1[0]["Name"], records2[0]["Name"])

            records3 = self.get_filtered_nba("Position == 'SG'", suffix=suffix, params="page=1")
            self.assertEqual(len(records3), DEFAULT_PAGE_SIZE)
            self.assertEqual(records1[DEFAULT_PAGE_SIZE]["Name"], records3[0]["Name"])

            records4 = self.get_filtered_nba("Position == 'SG'", suffix=suffix, params="page=1&page_size=10")
            self.assertEqual(len(records4), 10)
            self.assertEqual(records4[0]["Name"], records1[10]["Name"])
            self.assertEqual(records4[0]["Name"], "Arron Afflalo")

    @tag("query")
    def test_dataset_filtering_bad_query(self):
        for suffix in TEST_DATA_SUFFIXES:
            response = self.get_filtered_nba(
                "MISSING_COLUMN == 'SG'", suffix=suffix, status_code=status.HTTP_400_BAD_REQUEST
            )
            data = response.data
            self.assertEqual(data["error"]["code"], "error")
            self.assertEqual(data["error"]["meta"]["extra"]["error"], "name 'MISSING_COLUMN' is not defined")
            self.assertEqual(data["error"]["meta"]["extra"]["query"], "MISSING_COLUMN == 'SG'")

    @tag("query")
    def test_dataset_filtering_sort(self):
        for suffix in TEST_DATA_SUFFIXES:
            records1 = self.get_filtered_nba(sort="Salary", suffix=suffix)
            self.assertEqual(len(records1), DEFAULT_PAGE_SIZE)
            for i in range(1, len(records1)):
                s1 = records1[i - 1]["Salary"]
                s2 = records1[i]["Salary"]
                if s1 and s2:
                    self.assertLessEqual(s1, s2)

            records2 = self.get_filtered_nba(sort="-Salary", suffix=suffix)
            self.assertEqual(len(records2), DEFAULT_PAGE_SIZE)
            for i in range(1, len(records2)):
                s1 = records2[i - 1]["Salary"]
                s2 = records2[i]["Salary"]
                if s1 and s2:
                    self.assertGreaterEqual(s1, s2)

    @tag("query")
    def test_dataset_filtering_sort_multiple(self):
        for suffix in TEST_DATA_SUFFIXES:
            records1 = self.get_filtered_nba(sort="Position,Salary", suffix=suffix)
            self.assertEqual(len(records1), DEFAULT_PAGE_SIZE)
            for i in range(1, len(records1)):
                p1 = records1[i - 1]["Position"]
                p2 = records1[i]["Position"]
                if p1 == p2:
                    s1 = records1[i - 1]["Salary"]
                    s2 = records1[i]["Salary"]
                    if s1 and s2:
                        self.assertLessEqual(s1, s2)

            records2 = self.get_filtered_nba(sort="Position,-Salary", suffix=suffix)
            self.assertEqual(len(records2), DEFAULT_PAGE_SIZE)
            for i in range(1, len(records2)):
                p1 = records1[i - 1]["Position"]
                p2 = records1[i]["Position"]
                if p1 == p2:
                    s1 = records2[i - 1]["Salary"]
                    s2 = records2[i]["Salary"]
                    if s1 and s2:
                        self.assertGreaterEqual(s1, s2)

    ##
    ## Metadata and statistical information from files as json
    ##

    def test_dataset_metadata_describe(self):
        for suffix in TEST_DATA_SUFFIXES:
            url = self.upload_dataset(dataset="nba", suffix=suffix)
            response = self.client.get(url + "?metadata=true&refresh=true")
            self.assertStatusCode(response)

            metadata = response.data[0]["attributes"]["metadata"]
            self.assertEqual(metadata["total_records"], 457)

            self.assertAlmostEqual(metadata["describe"]["Age"]["min"], 19.0, places=2)
            self.assertAlmostEqual(metadata["describe"]["Age"]["mean"], 26.93873, places=2)
            self.assertAlmostEqual(metadata["describe"]["Age"]["max"], 40.0, places=2)

            self.assertAlmostEqual(metadata["describe"]["Salary"]["25%"], 1_044_792.25, places=2)
            self.assertAlmostEqual(metadata["describe"]["Salary"]["50%"], 2_839_073.0, places=2)
            self.assertAlmostEqual(metadata["describe"]["Salary"]["75%"], 6_500_000.0, places=2)
