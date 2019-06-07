import io
import os
import os.path
import pytest
import pandas as pd

from random import random
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime
from django.utils.crypto import get_random_string

import django.utils.http
import django.core.files
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from analitico.utilities import read_json, get_dict_dot

import analitico
import api.models
from api.models import Dataset
from .utils import AnaliticoApiTestCase

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets/"


@pytest.mark.django_db
class ParquetTests(AnaliticoApiTestCase):
    def _upload_dog(self):
        """ The same dog image is used in a number of tests """
        url = reverse("api:workspace-asset-detail", args=("ws_storage_gcs", "assets", "oh-my-dog.jpg"))
        response = self.upload_file(url, "image_dog1.jpg", "image/jpeg", token=self.token1)
        self.assertEqual(response.data[0]["id"], "oh-my-dog.jpg")
        self.assertEqual(response.data[0]["path"], "workspaces/ws_storage_gcs/assets/oh-my-dog.jpg")
        self.assertEqual(response.data[0]["hash"], "a9f659efd070f3e5b121a54edd8b13d0")
        self.assertEqual(response.data[0]["url"], "analitico://workspaces/ws_storage_gcs/assets/oh-my-dog.jpg")
        return url, response

    def setUp(self):
        self.setup_basics()
        self.ds1 = Dataset(workspace=self.ws1, id="ds_1", title="Dataset1")
        self.ds1.save()

    ##
    ## Workspace storage
    ##

    def get_random_dataframe(self, rows=10 * 1000):
        return pd.DataFrame(
            {
                "String": [get_random_string(length=32) for _ in range(rows)],
                "Int": [int(1000 * random()) for _ in range(rows)],
                "Float": [random() for _ in range(rows)],
            }
        )

    def test_parquet_upload(self):

        df = self.get_random_dataframe()
        self.assertIsNotNone(df)

        factory = analitico.authorize("tok_demo1_croJ7gVp4cW9")
        response = factory.upload("ds_WKIIILcZg9rF", df, "random-table.parquet")
        self.assertIsNotNone(response)

    def test_parquet_upload_via_sdk(self):
        df = self.get_random_dataframe()
        self.assertIsNotNone(df)

        factory = analitico.authorize("tok_demo1_croJ7gVp4cW9")
        response = factory.upload("ds_WKIIILcZg9rF", df, "random-table.parquet")
        self.assertIsNotNone(response)
