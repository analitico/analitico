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


class ServerPluginTests(APITestCase):
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
        pass
