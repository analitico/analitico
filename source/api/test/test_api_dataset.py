import io
import os
import os.path
import numpy as np
import pandas as pd
import tempfile
import random
import string

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime
from django.core.files.uploadedfile import SimpleUploadedFile

import django.utils.http
import django.core.files

from rest_framework import status
from rest_framework.test import APITestCase
from analitico.utilities import read_json, get_dict_dot, time_ms, logger

import analitico.plugin
import api.models
from api.models import Job
from .utils import APITestCase
from analitico import ACTION_PROCESS
from api.pagination import MIN_PAGE_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class DatasetTests(APITestCase):
    """ Test datasets operations like uploading assets, processing pipelines, downloading data, etc """

    def _upload_titanic(self, dataset_id="ds_titanic_1", asset_name="titanic_1.csv", asset_class="assets"):
        url = reverse("api:dataset-asset-detail", args=(dataset_id, asset_class, asset_name))
        response = self.upload_file(url, asset_name, "text/csv", token=self.token1)
        self.assertEqual(response.data[0]["id"], asset_name)
        path = "workspaces/ws_samples/datasets/{}/{}/{}".format(dataset_id, asset_class, asset_name)
        self.assertEqual(response.data[0]["path"], path)
        return url, response

    def upload_large_random_data_csv(self, dataset_id, N=10000, k=5):
        df = pd.DataFrame(
            {
                "Number": range(0, N, 1),
                "Random": np.random.randint(k, k + 100, size=N),
                "String": pd.Series(random.choice(string.ascii_uppercase) for _ in range(N)),
            }
        )
        with tempfile.NamedTemporaryFile(suffix=".csv") as csv_file:
            df.to_csv(csv_file.name)
            self.assertTrue(os.path.isfile(csv_file.name))
            csv_file.seek(0)
            url = reverse("api:dataset-asset-detail", args=(dataset_id, "data", "data.csv"))
            response = self.upload_file(url, csv_file.name, "text/csv", token=self.token1)
            self.assertEqual(response.data[0]["id"], "data.csv")

    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:workspace-list")
            self.upload_items(url, api.models.WORKSPACE_PREFIX)
            url = reverse("api:dataset-list")
            self.upload_items(url, api.models.DATASET_PREFIX)
        except Exception as exc:
            print(exc)
            raise exc

    def test_dataset_get_titanic(self):
        """ Test getting a dataset """
        item = self.get_item("dataset", "ds_titanic_1", self.token1)
        self.assertEqual(item["id"], "ds_titanic_1")
        self.assertEqual(item["attributes"]["title"], "Kaggle - Titanic training dataset (train.csv)")
        self.assertEqual(item["attributes"]["description"], "https://www.kaggle.com/c/titanic")

    def test_dataset_get_titanic_upload_csv(self):
        """ Test uploading csv as a dataset asset """
        # no assets before uploading
        ds_url = reverse("api:dataset-detail", args=("ds_titanic_1",))
        ds_response = self.client.get(ds_url, format="json")
        ds_data1 = ds_response.data
        self.assertTrue("assets" not in ds_data1["attributes"])

        # upload titanic_1.csv
        asset_url, asset_response = self._upload_titanic("ds_titanic_1")
        ds_asset1 = asset_response.data[0]
        self.assertEqual(ds_asset1["id"], "titanic_1.csv")
        self.assertEqual(ds_asset1["filename"], "titanic_1.csv")
        self.assertEqual(ds_asset1["content_type"], "text/csv")
        self.assertEqual(ds_asset1["size"], 61194)

        # check dataset again, this time should have assets
        ds_response2 = self.client.get(ds_url, format="json")
        ds_data2 = ds_response2.data
        self.assertTrue("assets" in ds_data2["attributes"])
        ds_asset2 = ds_data2["attributes"]["assets"][0]

        # assets from upload same as one from later query
        self.assertEqual(ds_asset2["id"], "titanic_1.csv")
        self.assertEqual(ds_asset2["filename"], "titanic_1.csv")
        self.assertEqual(ds_asset2["content_type"], "text/csv")
        self.assertEqual(ds_asset2["size"], 61194)

    def test_dataset_job_action_unsupported(self):
        """ Test requesting a job with an action that is not supported """
        job_url = reverse("api:dataset-job-action", args=("ds_titanic_1", "bogus_action"))
        job_response = self.client.post(job_url, format="json")
        self.assertEqual(job_response.status_code, 405)
        self.assertEqual(job_response.status_text, "Method Not Allowed")

    def test_dataset_job_action_process(self):
        """ Test uploading csv then requesting to process it """
        asset_url, asset_response = self._upload_titanic("ds_titanic_1")

        # request job processing
        job_url = reverse("api:dataset-job-action", args=("ds_titanic_1", ACTION_PROCESS))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data

        # check job that was created
        self.assertEqual(job_data["id"][:3], "jb_")
        self.assertEqual(job_data["type"], "job")
        self.assertEqual(job_data["attributes"]["item_id"], "ds_titanic_1")
        self.assertEqual(job_data["attributes"]["workspace_id"], "ws_samples")
        self.assertEqual(job_data["attributes"]["action"], "dataset/process")
        # self.assertEqual(job_data["attributes"]["status"], Job.JOB_STATUS_RUNNING)

    def test_dataset_job_action_process_with_extra_query_values(self):
        """ Test requesting a process action with additional query_values """
        job_url = reverse("api:dataset-job-action", args=("ds_titanic_1", ACTION_PROCESS))
        job_response = self.client.post(job_url, {"extra1": "value1", "extra2": "value2"})
        job_data = job_response.data

        # TODO check job that was created has extra params
        self.assertEqual(job_data["attributes"]["item_id"], "ds_titanic_1")
        self.assertEqual(job_data["attributes"]["workspace_id"], "ws_samples")
        self.assertEqual(job_data["attributes"]["action"], "dataset/process")

    def test_dataset_job_action_process_completed_url_asset(self):
        """ Test uploading csv then requesting to process it and checking that it completed """
        # request job processing
        job_url = reverse("api:dataset-job-action", args=("ds_titanic_2", ACTION_PROCESS))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_data["attributes"]["status"], "completed")

        # check dataset again, this time should have data asset
        ds_url = reverse("api:dataset-detail", args=("ds_titanic_2",))
        ds_response = self.client.get(ds_url, format="json")
        ds_data = ds_response.data
        self.assertEqual(len(ds_data["attributes"]["data"]), 1)
        ds_asset = ds_data["attributes"]["data"][0]
        self.assertEqual(ds_asset["id"], "data.csv")
        self.assertEqual(ds_asset["filename"], "data.csv")
        self.assertEqual(ds_asset["content_type"], "text/csv")
        self.assertTrue("schema" in ds_asset)

        # dataset should have schema
        ds_columns = ds_asset["schema"]["columns"]
        self.assertEqual(len(ds_columns), 12)
        self.assertEqual(ds_columns[0]["name"], "PassengerId")
        self.assertEqual(ds_columns[0]["type"], "integer")

        # retrieve asset info by itself using asset/json endpoint
        meta_url = reverse("api:dataset-asset-detail-info", args=("ds_titanic_2", "data", "data.csv"))
        meta_response = self.client.get(meta_url)
        self.assertEqual(meta_response["Content-Type"], "application/json")
        self.assertIsNotNone(meta_response.data)
        meta = meta_response.data
        self.assertEqual(meta["content_type"], "text/csv")
        self.assertEqual(meta["filename"], "data.csv")
        self.assertEqual(meta["id"], "data.csv")
        self.assertEqual(meta["path"], "workspaces/ws_samples/datasets/ds_titanic_2/data/data.csv")
        self.assertEqual(meta["url"], "analitico://datasets/ds_titanic_2/data/data.csv")

    def test_dataset_job_action_process_csv_from_analitico_asset(self):
        """ Test uploading csv then requesting to process it and checking that it completed """

        # upload titanic_1.csv
        asset_url, asset_response = self._upload_titanic("ds_titanic_3")
        ds_asset1 = asset_response.data[0]
        self.assertEqual(ds_asset1["id"], "titanic_1.csv")

        # request job processing
        job_url = reverse("api:dataset-job-action", args=("ds_titanic_3", ACTION_PROCESS))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_data["attributes"]["status"], "completed")

    def test_dataset_job_action_process_csv_with_no_plugins(self):
        """ Test uploading csv then requesting to process it and checking that a plugin is created and schema filled """
        # upload titanic_1.csv
        asset_url, asset_response = self._upload_titanic("ds_titanic_4")
        ds_asset = asset_response.data[0]
        self.assertEqual(ds_asset["id"], "titanic_1.csv")

        # request dataset job processing (dataset has 1 csv asset and no plugins)
        job_url = reverse("api:dataset-job-action", args=("ds_titanic_4", ACTION_PROCESS))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_data["attributes"]["status"], "completed")

        # check dataset, now it should have an automatically created dataset pipeline plugin + schema
        ds_url = reverse("api:dataset-detail", args=("ds_titanic_4",))
        ds_response = self.client.get(ds_url, format="json")
        ds_data = ds_response.data
        self.assertTrue("plugin" in ds_data["attributes"])
        ds_pipe_plugin = ds_data["attributes"]["plugin"]
        self.assertEqual(ds_pipe_plugin["type"], analitico.plugin.PLUGIN_TYPE)
        self.assertEqual(ds_pipe_plugin["name"], analitico.plugin.DATAFRAME_PIPELINE_PLUGIN)

        # inside the pipeline plugin we should have a csv source plugin
        ds_csv_plugin = ds_pipe_plugin["plugins"][0]
        self.assertEqual(ds_csv_plugin["type"], analitico.plugin.PLUGIN_TYPE)
        self.assertEqual(ds_csv_plugin["name"], analitico.plugin.CSV_DATAFRAME_SOURCE_PLUGIN)
        self.assertEqual(ds_csv_plugin["source"]["content_type"], "text/csv")

        # csv source should be prepopulated with schema
        ds_schema = ds_csv_plugin["source"]["schema"]
        self.assertEqual(len(ds_schema["columns"]), 12)

        # retrieve data.csv (output) info and check for schema
        meta_url = reverse("api:dataset-asset-detail-info", args=("ds_titanic_4", "data", "data.csv"))
        meta_response = self.client.get(meta_url)
        self.assertEqual(meta_response["Content-Type"], "application/json")
        self.assertIsNotNone(meta_response.data)
        meta = meta_response.data
        self.assertEqual(meta["content_type"], "text/csv")
        self.assertEqual(meta["filename"], "data.csv")
        self.assertEqual(meta["id"], "data.csv")
        self.assertEqual(meta["path"], "workspaces/ws_samples/datasets/ds_titanic_4/data/data.csv")
        self.assertEqual(meta["url"], "analitico://datasets/ds_titanic_4/data/data.csv")
        self.assertTrue("schema" in meta)
        self.assertEqual(len(meta["schema"]["columns"]), 12)

    def test_dataset_upoload_process_data(self):
        """ Test uploading csv then requesting to process it with data/process endpoint """
        # upload titanic_1.csv
        asset_url, asset_response = self._upload_titanic("ds_titanic_4")
        ds_asset = asset_response.data[0]
        self.assertEqual(ds_asset["id"], "titanic_1.csv")

        # request dataset job processing (dataset has 1 csv asset and no plugins)
        job_url = reverse("api:dataset-detail-data-process", args=("ds_titanic_4",))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_data["attributes"]["status"], "completed")

    def test_dataset_upload_process_data_get_csv(self):
        """ Test uploading csv, processing, downloading csv """
        # upload and process titanic_1.csv
        asset_url, asset_response = self._upload_titanic("ds_titanic_4")
        ds_asset = asset_response.data[0]
        self.assertEqual(ds_asset["id"], "titanic_1.csv")

        # request dataset job processing (dataset has 1 csv asset and no plugins)
        job_url = reverse("api:dataset-detail-data-process", args=("ds_titanic_4",))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_data["attributes"]["status"], "completed")

        # request data download, check that it is streaming
        csv_url = reverse("api:dataset-detail-data-csv", args=("ds_titanic_4",))
        csv_response = self.client.get(csv_url)
        self.assertEqual(csv_response.status_code, 200)
        self.assertTrue(csv_response.streaming)
        csv = csv_response.streaming_content
        csv_data = csv_response.getvalue().decode("utf-8")
        # note that csv header starts with PassengerId because pandas implicit index was not saved (by design)
        csv_header = "PassengerId,Survived,Pclass,Name,Sex,Age,SibSp,Parch,Ticket,Fare,Cabin,Embarked\n"
        self.assertTrue(csv_data.startswith(csv_header))

    def test_dataset_upload_process_data_get_info(self):
        """ Test uploading csv, processing, downloading info on csv """
        # upload and process titanic_1.csv
        asset_url, asset_response = self._upload_titanic("ds_titanic_4")
        ds_asset = asset_response.data[0]
        self.assertEqual(ds_asset["id"], "titanic_1.csv")

        # request dataset job processing (dataset has 1 csv asset and no plugins)
        job_url = reverse("api:dataset-detail-data-process", args=("ds_titanic_4",))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_data["attributes"]["status"], "completed")

        # request information on data, check schema is present
        info_url = reverse("api:dataset-detail-data-info", args=("ds_titanic_4",))
        info_response = self.client.get(info_url)
        self.assertEqual(info_response.status_code, 200)
        self.assertFalse(info_response.streaming)
        info_data = info_response.data
        self.assertEqual(len(info_data["schema"]["columns"]), 12)

    def test_dataset_paging_no_parameters_no_meta(self):
        """ Test uploading a large csv then downloading as json in pages """
        self.upload_large_random_data_csv("ds_titanic_4", 500)
        # do not indicate ?meta, defaults to false
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), 25)
        self.assertEqual(records[0]["Number"], 0)
        self.assertEqual(records[24]["Number"], 24)
        self.assertTrue("meta" not in response.data)
        # indicate ?meta=False
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?meta=False"
        response = self.client.get(url)
        self.assertTrue("meta" not in response.data)

    def test_dataset_paging_no_parameters_with_meta(self):
        self.upload_large_random_data_csv("ds_titanic_4", 496)
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?meta=yes"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), 25)
        self.assertEqual(records[0]["Number"], 0)
        self.assertEqual(records[24]["Number"], 24)
        # metadata is optional
        meta = response.data["meta"]
        self.assertEqual(meta["page"], 0)
        self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
        self.assertEqual(meta["total_pages"], 20)
        self.assertEqual(meta["total_records"], 496)

    def test_dataset_paging_no_parameters(self):
        """ Test uploading a large csv then downloading as json in pages """
        self.upload_large_random_data_csv("ds_titanic_4", 500)

        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?meta=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), 25)
        self.assertEqual(records[0]["Number"], 0)
        self.assertEqual(records[24]["Number"], 24)
        meta = response.data["meta"]
        self.assertEqual(meta["page"], 0)
        self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
        self.assertEqual(meta["total_records"], 500)

    def test_dataset_paging_second_page(self):
        self.upload_large_random_data_csv("ds_titanic_4", 500)

        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?page=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), 25)
        self.assertEqual(records[0]["Number"], 25)
        self.assertEqual(records[24]["Number"], 49)

    def test_dataset_paging_last_page(self):
        self.upload_large_random_data_csv("ds_titanic_4", 490)
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?page=19&meta=True"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), 15)
        self.assertEqual(records[0]["Number"], 475)
        self.assertEqual(records[14]["Number"], 489)
        meta = response.data["meta"]
        self.assertEqual(meta["page"], 19)
        self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
        self.assertEqual(meta["total_records"], 490)

    def test_dataset_paging_beyond_last_page(self):
        self.upload_large_random_data_csv("ds_titanic_4", 490)
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?page=20&meta=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), 0)
        meta = response.data["meta"]
        self.assertEqual(meta["page"], 20)
        self.assertEqual(meta["page_size"], DEFAULT_PAGE_SIZE)
        self.assertEqual(meta["total_records"], 490)
        # beyond last
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?page=310"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), 0)

    def test_dataset_paging_scan_pages_check_performance(self):
        self.upload_large_random_data_csv("ds_titanic_4", DEFAULT_PAGE_SIZE * 500)

        # first page loading time may be higher because cache is cold
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?page=0&meta=yes"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), DEFAULT_PAGE_SIZE)

        # WARNING: THIS TEST CHECKS PERFORMANCE AND WILL THROW IF THE LOOP IS SLOW
        # THIS MEANS THAT IF YOU SETUP A BREAKPOINT AND DEBUG THE CODE YOU WILL GET AN ASSERT
        total_ms = time_ms()
        for i in range(20, 60):
            loading_ms = time_ms()
            url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?page=" + str(i)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            records = response.data["data"]
            self.assertEqual(len(records), DEFAULT_PAGE_SIZE)
            self.assertEqual(records[0]["Number"], i * DEFAULT_PAGE_SIZE)
            self.assertEqual(records[24]["Number"], ((i + 1) * DEFAULT_PAGE_SIZE) - 1)
            self.assertTrue("meta" not in response.data)
            loading_ms = time_ms(loading_ms)
            self.assertLess(int(loading_ms), 100, "Page loading time should be under 100ms")
        total_ms = time_ms(total_ms)
        average_ms = float(total_ms) / 40
        self.assertLess(int(loading_ms), 50, "Average page loading time should be less than 50ms")
        logger.info("Average page loading time is " + str(average_ms) + " ms")

    def test_dataset_paging_larger_page(self):
        self.upload_large_random_data_csv("ds_titanic_4", 1000)
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?page=10&page_size=50&meta=tRUe"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), 50)
        self.assertEqual(records[0]["Number"], 500)
        self.assertEqual(records[49]["Number"], 549)
        meta = response.data["meta"]
        self.assertEqual(meta["page"], 10)
        self.assertEqual(meta["page_size"], 50)

    def test_dataset_paging_huge_page(self):
        self.upload_large_random_data_csv("ds_titanic_4", MAX_PAGE_SIZE * 20)
        url = reverse("api:dataset-detail-data-json", args=("ds_titanic_4",)) + "?page=10&page_size=500&meta=yES"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data["data"]
        self.assertEqual(len(records), MAX_PAGE_SIZE)
        self.assertEqual(records[0]["Number"], MAX_PAGE_SIZE * 10)  # constrained to max_page_size
        meta = response.data["meta"]
        self.assertEqual(meta["page"], 10)
        self.assertEqual(meta["page_size"], MAX_PAGE_SIZE)
