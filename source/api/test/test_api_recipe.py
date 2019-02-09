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
from rest_framework.test import APITestCase
from analitico.utilities import read_json, get_dict_dot

import analitico.plugin
import api.models
import api.plugin
from api.models import Job, Endpoint
from .utils import APITestCase


# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class RecipeTests(APITestCase):
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
            self.upload_items(url, api.models.WORKSPACE_PREFIX)
            url = reverse("api:dataset-list")
            self.upload_items(url, api.models.DATASET_PREFIX)
            url = reverse("api:recipe-list")
            self.upload_items(url, api.models.RECIPE_PREFIX)
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
        url = reverse("api:recipe-job-action", args=("rx_housesalesprediction_1", "train"))
        response = self.client.get(url, format="json", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    def test_recipe_train_predict_the_whole_enchilada(self):
        """ 
        A fairly complicated end to end test:
        - create a dataset and process it
        - create a recipe and train model with dataset
        - create an endpoint and run predictions on model
        """
        try:
            # process source dataset
            self.auth_token(self.token1)
            url = reverse("api:dataset-job-action", args=("ds_housesalesprediction_1", "process"))
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
            url = reverse("api:recipe-job-action", args=("rx_housesalesprediction_1", "train"))
            response = self.client.post(url, format="json", status_code=status.HTTP_201_CREATED)

            # job from recipe train action
            job = response.data
            self.assertIsInstance(job, dict)
            self.assertEqual(job["type"], "job")
            self.assertTrue(job["id"].startswith(api.models.JOB_PREFIX))
            self.assertEqual(job["attributes"]["status"], "completed")

            # trained model from job
            model_id = job["attributes"]["model_id"]
            url = reverse("api:model-detail", args=(model_id,))
            response = self.client.get(url, format="json")
            model = response.data
            self.assertEqual(model["type"], "model")
            self.assertEqual(model["id"], model_id)

            # training results from model
            training = model["attributes"]["training"]
            self.assertEqual(training["type"], "analitico/training")
            self.assertEqual(training["plugins"]["training"], analitico.plugin.CATBOOST_REGRESSOR_PLUGIN)

            # create an endpoint that can serve inferences based on trained model
            url = reverse("api:endpoint-list")
            response = self.client.post(
                url,
                data={
                    "workspace": model["attributes"]["workspace"],
                    "model_id": model_id,
                    "plugin": {
                        "type": analitico.plugin.PLUGIN_TYPE,
                        "name": analitico.plugin.ENDPOINT_PIPELINE_PLUGIN,
                        "plugins": [{"type": analitico.plugin.PLUGIN_TYPE, "name": training["plugins"]["prediction"]}],
                    },
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            endpoint = response.data
            endpoint_id = endpoint["id"]
            self.assertTrue(endpoint["id"].startswith(api.models.ENDPOINT_PREFIX))
            self.assertEquals(endpoint["attributes"]["model_id"], model_id)
            self.assertEquals(endpoint["attributes"]["plugin"]["type"], analitico.plugin.PLUGIN_TYPE)
            self.assertEquals(endpoint["attributes"]["plugin"]["name"], analitico.plugin.ENDPOINT_PIPELINE_PLUGIN)

            # load some data that we want to run predictions on
            num_predictions = 20  # number of test predictions to run
            homes_path = self.get_asset_path("kc_house_data.csv")
            homes = pd.read_csv(homes_path).head(num_predictions)  # just a sample
            homes_dict = homes.to_dict(orient="records")

            # run predictions one at a time
            predict_url = reverse("api:endpoint-job-action", args=(endpoint_id, "predict"))
            for home in homes_dict:
                priceless_home = home.copy()
                priceless_home.pop("price")
                predict_response = self.client.post(predict_url, priceless_home, format="json")
                predict_data = predict_response.data
                predict_price = predict_data["attributes"]["payload"]["predictions"][0]
                print("House price: " + str(home["price"]) + ", predicted price: " + str(predict_price))
                self.assertTrue(predict_price > 0)
                # TODO check job layout

            # run a bunch of predictions at once
            priceless_homes = homes.drop(["price"], axis=1)
            priceless_dict = priceless_homes.to_dict(orient="records")
            preds2_response = self.client.post(predict_url, priceless_dict, format="json")
            preds2_data = preds2_response.data
            self.assertEqual(len(preds2_data["attributes"]["payload"]["predictions"]), len(priceless_homes))

        except Exception as exc:
            raise exc

    # TODO pass train and test sets with a column with different names

    # TODO pass train and test sets with a column with different type
