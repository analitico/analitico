import json
import requests

from django.urls import reverse
from django.test import tag
from rest_framework import status

from api.models import *
from .utils import AnaliticoApiTestCase
from analitico.utilities import id_generator
from api.k8 import kubectl, K8_STAGE_PRODUCTION, K8_DEFAULT_NAMESPACE, k8_normalize_name
from api.kubeflow import automl_convert_request_for_prediction, tensorflow_serving_deploy


class AutomlTests(AnaliticoApiTestCase):

    # id of the recipe already run on Kubeflow Pipeline to 
    # use for testing artifacts or predictions
    run_recipe_id = "rx_iris_automl_unittest"
    # run recipe's workspace id 
    workspace_id = "ws_y1ehlz2e"

    @tag("live", "slow")
    def OFF_test_automl_run(self):
        try:
            # create a recipe with automl configs
            recipe = Recipe.objects.create(pk=self.run_recipe_id, workspace_id=self.ws1.id)
            recipe.set_attribute(
                "automl",
                {
                    "workspace_id": self.ws1.id,
                    "recipe_id": self.run_recipe_id,
                    "data_item_id": self.run_recipe_id,
                    "data_path": "data",
                    "prediction_type": "regression",
                    "target_column": "target",
                },
            )
            recipe.save()
            # upload dataset used by pipeline
            self.auth_token(self.token1)
            data_url = url = reverse("api:recipe-files", args=(recipe.id, "data/iris.csv"))
            self.upload_file(
                data_url,
                "../../../../automl/mount/recipes/rx_iris/data/iris.csv",
                content_type="text/csv",
                token=self.token1,
            )

            # user cannot run automl he doesn't have access to
            self.auth_token(self.token2)
            url = reverse("api:recipe-automl-run", args=(recipe.id,))
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # without automl_config
            self.auth_token(self.token2)
            recipe_without_automl_config = Recipe.objects.create(
                pk="rx_without_automl_config", workspace_id=self.ws2.id
            )
            url = reverse("api:recipe-automl-run", args=(recipe_without_automl_config.id,))
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

            # user can run an automl config on its recipe
            # request to run the pipeline
            self.auth_token(self.token1)
            url = reverse("api:recipe-automl-run", args=(recipe.id,))
            response = self.client.post(url)
            self.assertApiResponse(response)

            data = response.json().get("data")
            attributes = data["attributes"]

            # not yet started
            self.assertIn("automl", attributes)
            self.assertIsNotNone(attributes["automl"])
            # run id is saved in automl config
            recipe.refresh_from_db()
            self.assertEqual(attributes["automl"]["run_id"], recipe.get_attribute("automl.run_id"))

            # the run of a pipeline create the endpoint service.
            # It raises 404 exception in case of error
            kubectl("cloud", "get", "service/ws-001")
        finally:
            try:
                kubectl("cloud", "delete", "service/ws-001", output=None)
            except:
                pass

    @tag("slow")
    def OFF_test_automl_convert_predict_request(self):
        recipe = Recipe.objects.create(pk=self.run_recipe_id, workspace_id=self.ws2.id)

        # single prediction
        content = automl_convert_request_for_prediction(
            recipe,
            '{ "instances": [ {"sepal_length":[6.4], "sepal_width":[2.8], "petal_length":[5.6], "petal_width":[2.2]} ] }',
        )
        content = json.loads(content)
        self.assertIn("instances", content)
        self.assertEqual(1, len(content["instances"]))
        self.assertIn("b64", content["instances"][0])
        self.assertTrue(content["instances"][0]["b64"])

        # multiple predictions
        content = automl_convert_request_for_prediction(
            recipe,
            '{ "instances": [ {"sepal_length":[6.4], "sepal_width":[2.8], "petal_length":[5.6], "petal_width":[2.2]}, {"sepal_length":[6.4], "sepal_width":[2.8], "petal_length":[5.6], "petal_width":[2.2]} ] }',
        )
        content = json.loads(content)
        self.assertIn("instances", content)
        self.assertEqual(2, len(content["instances"]))
        self.assertIn("b64", content["instances"][0])
        self.assertTrue(content["instances"][0]["b64"])
        self.assertIn("b64", content["instances"][1])
        self.assertTrue(content["instances"][1]["b64"])

    @tag("slow")
    def OFF_test_predict(self):
        url = f"https://api-staging.cloud.analitico.ai/api/recipes/{self.run_recipe_id}/automl/predict"
        content = '{ "instances": [ {"sepal_length":[6.4], "sepal_width":[2.8], "petal_length":[5.6], "petal_width":[2.2]} ] }'

        # user cannot request prediction of an item he doesn't have access to
        self.auth_token(self.token2)
        response = requests.post(url, data=content, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        response = requests.post(url, data=content, content_type="application/json")
        self.assertApiResponse(response)

        prediction = response.json()
        self.assertIn("predictions", prediction)
        self.assertIn("scores", prediction["predictions"])
        self.assertEqual(prediction["predictions"]["scores"], [8.24773451e-06, 0.975438833, 0.0245529674])
        self.assertEqual(prediction["predictions"]["classes"], [0, 1, 2])

    def OFF_test_model_schema(self):
        # artifacts from the pipeline of the recipe are loaded on the ws2 drive
        recipe = Recipe.objects.create(pk=self.run_recipe_id, workspace_id=self.workspace_id)
        recipe.save()
        url = reverse("api:recipe-automl-schema", args=(recipe.id, ))

        # user cannot request model schema of an item he doesn't have access to
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        response = self.client.get(url)
        self.assertApiResponse(response)

        schema = response.json()
        self.assertIn("petal_length", schema)
        self.assertIn("petal_width", schema)
        self.assertIn("sepal_length", schema)
        self.assertIn("sepal_width", schema)

    def OFF_test_model_statistics(self):
        # artifacts from the pipeline of the recipe are loaded on the ws2 drive
        recipe = Recipe.objects.create(pk=self.run_recipe_id, workspace_id=self.ws2.id)
        recipe.save()
        url = reverse("api:recipe-automl-statistics", args=(recipe.id, ))

        # user cannot request model statistics of an item he doesn't have access to
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token2)
        response = self.client.get(url)
        self.assertApiResponse(response)

        schema = response.json()
        self.assertIn("petal_length", schema)
        self.assertIn("petal_width", schema)
        self.assertIn("sepal_length", schema)
        self.assertIn("sepal_width", schema)