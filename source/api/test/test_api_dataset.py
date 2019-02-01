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

import api.models
from api.models import Job
from .utils import APITestCase


# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class DatasetTests(APITestCase):
    """ Test datasets operations like uploading assets, processing pipelines, downloading data, etc """

    def _upload_titanic(self, dataset_id="ds_titanic_1", asset_name="titanic_1.csv"):
        url = reverse("api:dataset-asset-detail", args=(dataset_id, "assets", asset_name))
        response = self._upload_file(url, asset_name, "text/csv", token=self.token1)
        self.assertEqual(response.data[0]["id"], asset_name)
        path = "workspaces/ws_samples/datasets/" + dataset_id + "/assets/" + asset_name
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
        self.assertEqual(job_data["attributes"]["status"], Job.JOB_STATUS_PROCESSING)

    def test_dataset_job_action_unsupported(self):
        """ Test requesting a job with an action that is not supported """
        job_url = reverse("api:dataset-job-detail", args=("ds_titanic_1", "bogus_action"))
        job_response = self.client.post(job_url, format="json")
        self.assertEqual(job_response.status_code, 405)
        self.assertEqual(job_response.status_text, "Method Not Allowed")
