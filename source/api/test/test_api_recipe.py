import io
import os
import os.path
import pandas as pd

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime
from django.core.files.uploadedfile import SimpleUploadedFile

import django.utils.http
import django.core.files

from rest_framework import status
from analitico.utilities import read_json, get_dict_dot

import analitico
import analitico.plugin
import api.models
import api.plugin

from api.models import Job, Endpoint, Recipe, Model, Endpoint
from .utils import AnaliticoApiTestCase


# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class RecipeTests(AnaliticoApiTestCase):
    """ Test recipe operations like creating and training models """

    def _upload_titanic(self, dataset_id="ds_titanic_1", asset_name="titanic_1.csv", asset_class="assets"):
        url = reverse("api:dataset-asset-detail", args=(dataset_id, asset_class, asset_name))
        response = self.upload_file(url, asset_name, "text/csv", token=self.token1)
        self.assertEqual(response.data[0]["id"], asset_name)
        path = "workspaces/ws_samples/datasets/{}/{}/{}".format(dataset_id, asset_class, asset_name)
        self.assertEqual(response.data[0]["path"], path)
        return url, response

    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:workspace-list")
            self.upload_items(url, analitico.WORKSPACE_PREFIX)
            url = reverse("api:dataset-list")
            self.upload_items(url, analitico.DATASET_PREFIX)
            url = reverse("api:recipe-list")
            self.upload_items(url, analitico.RECIPE_PREFIX)
        except Exception as exc:
            print(exc)
            raise exc

    def test_recipe_get_list_no_token(self):
        """ Test getting a list of recipes without a token """
        self.auth_token(None)
        url = reverse("api:recipe-list")
        self.client.get(url, format="json", status_code=status.HTTP_403_FORBIDDEN)

    def test_recipe_get_list(self):
        """ Test getting a list of recipes """
        self.auth_token(self.token1)
        url = reverse("api:recipe-list")
        response = self.client.get(url, format="json", status_code=status.HTTP_200_OK)

        data = response.data
        self.assertEqual(len(data), 1)

        recipe = data[0]
        self.assertEqual(recipe["type"], "analitico/recipe")
        self.assertEqual(recipe["id"], "rx_housesalesprediction_1")

    def test_recipe_get_detail_no_auth(self):
        """ Get a specific recipe without givin an auth token """
        self.auth_token(None)
        url = reverse("api:recipe-detail", args=("rx_housesalesprediction_1",))
        self.client.get(url, format="json", status_code=status.HTTP_403_FORBIDDEN)

    def test_recipe_get_detail(self):
        """ Get a specific recipe """
        self.auth_token(self.token1)
        url = reverse("api:recipe-detail", args=("rx_housesalesprediction_1",))
        response = self.client.get(url, format="json")

        recipe = response.data
        self.assertIsInstance(recipe, dict)
        self.assertEqual(recipe["type"], "analitico/recipe")
        self.assertEqual(recipe["id"], "rx_housesalesprediction_1")

    def test_recipe_train_method_not_allowed(self):
        """ Request training of a job using GET instead of POST """
        url = reverse("api:recipe-job-action", args=("rx_housesalesprediction_1", "train"))
        response = self.client.get(url, format="json", status_code=status.HTTP_406_NOT_ACCEPTABLE)
