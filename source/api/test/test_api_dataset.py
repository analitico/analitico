import io
import os
import os.path

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
from analitico.utilities import read_json, get_dict_dot

import analitico.plugin
import api.models
from api.models import Job
from .utils import APITestCase


# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class DatasetTests(APITestCase):
    """ Test datasets operations like uploading assets, processing pipelines, downloading data, etc """

    def _upload_titanic(self, dataset_id="ds_titanic_1", asset_name="titanic_1.csv", asset_class="assets"):
        url = reverse("api:dataset-asset-detail", args=(dataset_id, asset_class, asset_name))
        response = self._upload_file(url, asset_name, "text/csv", token=self.token1)
        self.assertEqual(response.data[0]["id"], asset_name)
        path = "analitico://workspaces/ws_samples/datasets/{}/{}/{}".format(dataset_id, asset_class, asset_name)
        self.assertEqual(response.data[0]["path"], path)
        return url, response

    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:workspace-list")
            self._upload_items(url, api.models.WORKSPACE_PREFIX)
            url = reverse("api:dataset-list")
            self._upload_items(url, api.models.DATASET_PREFIX)
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
        job_url = reverse("api:dataset-job-detail", args=("ds_titanic_1", "bogus_action"))
        job_response = self.client.post(job_url, format="json")
        self.assertEqual(job_response.status_code, 405)
        self.assertEqual(job_response.status_text, "Method Not Allowed")

    def test_dataset_job_action_process(self):
        """ Test uploading csv then requesting to process it """
        asset_url, asset_response = self._upload_titanic("ds_titanic_1")

        # request job processing
        job_url = reverse("api:dataset-job-detail", args=("ds_titanic_1", "process"))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data

        # check job that was created
        self.assertEqual(job_data["id"][:3], "jb_")
        self.assertEqual(job_data["type"], "job")
        self.assertEqual(job_data["attributes"]["item_id"], "ds_titanic_1")
        self.assertEqual(job_data["attributes"]["workspace"], "ws_samples")
        self.assertEqual(job_data["attributes"]["action"], "dataset/process")
        # self.assertEqual(job_data["attributes"]["status"], Job.JOB_STATUS_RUNNING)

    def test_dataset_job_action_process_with_extra_query_values(self):
        """ Test requesting a process action with additional query_values """
        job_url = reverse("api:dataset-job-detail", args=("ds_titanic_1", "process"))
        job_response = self.client.post(job_url, {"extra1": "value1", "extra2": "value2"})
        job_data = job_response.data

        # TODO check job that was created has extra params
        self.assertEqual(job_data["attributes"]["item_id"], "ds_titanic_1")
        self.assertEqual(job_data["attributes"]["workspace"], "ws_samples")
        self.assertEqual(job_data["attributes"]["action"], "dataset/process")

    def test_dataset_job_action_process_completed_url_asset(self):
        """ Test uploading csv then requesting to process it and checking that it completed """
        # request job processing
        job_url = reverse("api:dataset-job-detail", args=("ds_titanic_2", "process"))
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
        self.assertEqual(meta["path"], "analitico://workspaces/ws_samples/datasets/ds_titanic_2/data/data.csv")

    def test_dataset_job_action_process_csv_from_analitico_asset(self):
        """ Test uploading csv then requesting to process it and checking that it completed """

        # upload titanic_1.csv
        asset_url, asset_response = self._upload_titanic("ds_titanic_3")
        ds_asset1 = asset_response.data[0]
        self.assertEqual(ds_asset1["id"], "titanic_1.csv")

        # request job processing
        job_url = reverse("api:dataset-job-detail", args=("ds_titanic_3", "process"))
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
        job_url = reverse("api:dataset-job-detail", args=("ds_titanic_4", "process"))
        job_response = self.client.post(job_url, format="json")
        job_data = job_response.data
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_data["attributes"]["status"], "completed")

        # check dataset, now it should have an automatically created plugin + schema
        ds_url = reverse("api:dataset-detail", args=("ds_titanic_4",))
        ds_response = self.client.get(ds_url, format="json")
        ds_data = ds_response.data
        self.assertTrue("plugin" in ds_data["attributes"])
        ds_plugin = ds_data["attributes"]["plugin"]
        self.assertEqual(ds_plugin["type"], "analitico/plugin")
        self.assertEqual(ds_plugin["name"], analitico.plugin.CSV_DATAFRAME_SOURCE_PLUGIN)
        self.assertEqual(ds_plugin["source"]["content_type"], "text/csv")
        ds_schema = ds_plugin["source"]["schema"]
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
        self.assertEqual(meta["path"], "analitico://workspaces/ws_samples/datasets/ds_titanic_4/data/data.csv")
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
