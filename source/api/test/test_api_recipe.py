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


class RecipeTests(APITestCase):
    """ Test recipe operations like creating and training models """

    def _upload_titanic(self, dataset_id="ds_titanic_1", asset_name="titanic_1.csv", asset_class="assets"):
        url = reverse("api:dataset-asset-detail", args=(dataset_id, asset_class, asset_name))
        response = self._upload_file(url, asset_name, "text/csv", token=self.token1)
        self.assertEqual(response.data[0]["id"], asset_name)
        path = "workspaces/ws_samples/datasets/{}/{}/{}".format(dataset_id, asset_class, asset_name)
        self.assertEqual(response.data[0]["path"], path)
        return url, response

    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:workspace-list")
            self._upload_items(url, api.models.WORKSPACE_PREFIX)
            url = reverse("api:dataset-list")
            self._upload_items(url, api.models.DATASET_PREFIX)
            url = reverse("api:recipe-list")
            self._upload_items(url, api.models.RECIPE_PREFIX)
        except Exception as exc:
            print(exc)
            raise exc

    def test_recipe_get_list_no_token(self):
        """ Test getting a list of recipes without a token """
        self.auth_token(None)
        url = reverse("api:recipe-list")
        response = self.client.get(url, format="json", status_code=status.HTTP_403_FORBIDDEN)

    def test_recipe_get_list(self):
        """ Test getting a list of recipes """
        self.auth_token(self.token1)
        url = reverse("api:recipe-list")
        response = self.client.get(url, format="json", status_code=status.HTTP_200_OK)

        data = response.data
        self.assertEqual(len(data), 1)

        recipe = data[0]
        self.assertEqual(recipe["type"], "recipe")
        self.assertEqual(recipe["id"], "rx_housesalesprediction_1")

    def test_recipe_get_detail_no_auth(self):
        """ Get a specific recipe without givin an auth token """
        self.auth_token(None)
        url = reverse("api:recipe-detail", args=("rx_housesalesprediction_1",))
        response = self.client.get(url, format="json", status_code=status.HTTP_403_FORBIDDEN)

    def test_recipe_get_detail(self):
        """ Get a specific recipe """
        self.auth_token(self.token1)
        url = reverse("api:recipe-detail", args=("rx_housesalesprediction_1",))
        response = self.client.get(url, format="json")

        recipe = response.data
        self.assertIsInstance(recipe, dict)
        self.assertEqual(recipe["type"], "recipe")
        self.assertEqual(recipe["id"], "rx_housesalesprediction_1")

    def test_recipe_train_method_not_allowed(self):
        """ Request training of a job using GET instead of POST """
        url = reverse("api:recipe-job-detail", args=("rx_housesalesprediction_1", "train"))
        response = self.client.get(url, format="json", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    def test_recipe_train(self):
        """ Process a dataset, then train a recipe with it """
        try:
            self.auth_token(self.token1)

            # process source dataset
            url = reverse("api:dataset-job-detail", args=("ds_housesalesprediction_1", "process"))
            response = self.client.post(url, format="json")

            job = response.data
            self.assertEqual(job["type"], "job")
            self.assertTrue(job["id"].startswith(api.models.JOB_PREFIX))
            self.assertEqual(job["attributes"]["action"], "dataset/process")
            self.assertEqual(job["attributes"]["status"], "completed")
            self.assertEqual(job["attributes"]["workspace"], "ws_samples")
            self.assertEqual(job["attributes"]["item_id"], "ds_housesalesprediction_1")
            self.assertEqual(len(job["links"]), 2)  # self, related
            self.assertTrue("self" in job["links"])
            self.assertTrue("related" in job["links"])

            # train recipe using dataset output
            url = reverse("api:recipe-job-detail", args=("rx_housesalesprediction_1", "train"))
            response = self.client.post(url, format="json", status_code=status.HTTP_201_CREATED)

            recipe = response.data
            self.assertIsInstance(recipe, dict)
            self.assertEqual(recipe["type"], "recipe")
            self.assertEqual(recipe["id"], "rx_housesalesprediction_1")

        except Exception as exc:
            raise exc

    # TODO pass train and test sets with a column with different names

    # TODO pass train and test sets with a column with different type
