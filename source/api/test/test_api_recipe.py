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

    def OFFtest_recipe_train_predict_with_fake_notebook(self):
        """ Minimal test of fake notebook based recipe in Jupyter trained and used for predictions """
        try:
            notebook = self.read_notebook_asset("notebook08-predict-fake.ipynb")

            recipe = Recipe.objects.create(pk="rx_1", workspace=self.ws1)
            recipe.notebook = notebook
            recipe.save()

            # train recipe
            url = reverse("api:recipe-job-action", args=("rx_1", analitico.ACTION_TRAIN)) + "?async=false"
            response = self.client.post(url, format="json", status_code=status.HTTP_201_CREATED)

            # job from recipe train action
            job = response.data
            self.assertIsInstance(job, dict)
            self.assertEqual(job["type"], "analitico/job")
            self.assertTrue(job["id"].startswith(analitico.JOB_PREFIX))
            self.assertEqual(job["attributes"]["status"], "completed")

            # trained model from job
            model_id = job["attributes"]["model_id"]
            url = reverse("api:model-detail", args=(model_id,))
            response = self.client.get(url, format="json")
            model = response.data
            self.assertEqual(model["type"], "analitico/model")
            self.assertEqual(model["id"], model_id)

            # check that model has related links
            self.assertTrue(analitico.MODEL_PREFIX in model["links"]["self"])
            self.assertTrue(analitico.RECIPE_PREFIX in model["links"]["recipe"])
            self.assertTrue(analitico.JOB_PREFIX in model["links"]["job"])

            # create an endpoint that can serve inferences based on trained model
            url = reverse("api:endpoint-list")
            response = self.client.post(
                url, data={"workspace_id": model["attributes"]["workspace_id"], "model_id": model_id}
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            endpoint = response.data
            endpoint_id = endpoint["id"]
            self.assertTrue(endpoint["id"].startswith(analitico.ENDPOINT_PREFIX))
            self.assertEqual(endpoint["attributes"]["model_id"], model_id)

            # run predictions one by one
            predict_url = reverse("api:endpoint-predict", args=(endpoint_id,))
            for i in range(100, 150, 10):
                response = self.client.post(predict_url, [{"value": i}], format="json")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                # prediction is the "value" we sent plus 2
                self.assertEqual(response.data["predictions"][0], i + 2)

            # run predictions in a batch
            data = [{"value": 100 + i} for i in range(20)]
            response = self.client.post(predict_url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            for i in range(20):
                # prediction is the "value" we sent plus 2
                self.assertEqual(response.data["predictions"][i], 100 + i + 2)

        except Exception as exc:
            raise exc

    # TODO pass train and test sets with a column with different names

    # TODO pass train and test sets with a column with different type
