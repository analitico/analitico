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
    run_recipe_id = "rx_iris_labeled_automl_unittest"
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
            data_url = reverse("api:recipe-files", args=(recipe.id, "data/iris.csv"))
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
            kubectl("cloud", "get", "service/ws-001", context_name="admin@cloud-staging.analitico.ai")
        finally:
            try:
                kubectl("cloud", "delete", "service/ws-001", context_name="admin@cloud-staging.analitico.ai", output=None)
            except:
                pass

    def OFF_test_automl_convert_predict_request(self):
        recipe = Recipe.objects.create(pk=self.run_recipe_id, workspace_id=self.ws2.id)

        # single prediction
        content = automl_convert_request_for_prediction(
            recipe,
            { "instances": [ {"sepal_length":6.4, "sepal_width":2.8, "petal_length":5.6, "petal_width":2.2} ] },
        )
        content = json.loads(content)
        self.assertIn("instances", content)
        self.assertEqual(1, len(content["instances"]))
        self.assertIn("b64", content["instances"][0])
        self.assertTrue(content["instances"][0]["b64"])

        # multiple predictions
        content = automl_convert_request_for_prediction(
            recipe,
            { "instances": [ {"sepal_length":6.4, "sepal_width":2.8, "petal_length":5.6, "petal_width":2.2}, {"sepal_length":6.4, "sepal_width":2.8, "petal_length":5.6, "petal_width":2.2} ] },
        )
        content = json.loads(content)
        self.assertIn("instances", content)
        self.assertEqual(2, len(content["instances"]))
        self.assertIn("b64", content["instances"][0])
        self.assertTrue(content["instances"][0]["b64"])
        self.assertIn("b64", content["instances"][1])
        self.assertTrue(content["instances"][1]["b64"])

    def OFF_test_predict(self):
        # recipe's automl config has never run before and the predict cannot be performed
        recipe_automl_never_run = Recipe.objects.create(pk="rx_automl_config_never_run", workspace_id=self.ws1.id)
        recipe_automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:recipe-automl-predict", args=(recipe_automl_never_run.id, ))
        response = self.client.post(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)

        # model for prediction is served from the self.workspace_id's drive
        url = f"https://api-staging.cloud.analitico.ai/api/recipes/{self.run_recipe_id}/automl/predict"
        content = '{ "instances": [ {"sepal_length":6.4, "sepal_width":2.8, "petal_length":5.6, "petal_width":2.2} ] }'
        headers = {"Authorization": "Bearer tok_demo1_croJ7gVp4cW9", "Content-Type": "application/json"}

        # TODO: get_object() raises 404 not found
        # user can request prediction even without authentication
        response = requests.post(url, data=content)
        self.assertApiResponse(response)

        response = requests.post(url, data=content, headers=headers)
        self.assertApiResponse(response)

        predictions = response.json()
        self.assertIn("predictions", predictions)
        self.assertEqual(1, len(predictions))

        prediction = predictions["predictions"][0]
        self.assertIn("scores", prediction)
        self.assertEqual(prediction["scores"], [0.0199055225, 0.980042815, 5.1618179e-05])
        self.assertEqual(prediction["classes"], ['Versicolor', 'Virginica', 'Setosa'])

    def OFF_test_model_schema(self):
        # recipe's automl config has never run before and the schema
        # does not exist
        recipe_automl_never_run = Recipe.objects.create(pk="rx_automl_config_never_run", workspace_id=self.ws2.id)
        recipe_automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:recipe-automl-schema", args=(recipe_automl_never_run.id, ))
        response = self.client.get(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)

        # pre-generated artifacts are loaded in the `self.ws2` drive at:
        # //u206378@u206378.your-storagebox.de/user5-test/automl/rx_iris_unittest_artifacts/pipelines
        # URI to the artifacts are retrieved using `self.run_recipe_id` references in the mlmetadata-db.
        # In case of new runs of `self.run_recipe_id`'s automl pipeline, folder id in the above location 
        # must be changed accordingly.
        recipe = Recipe.objects.create(pk=self.run_recipe_id, workspace_id=self.ws2.id)
        recipe.save()
        url = reverse("api:recipe-automl-schema", args=(recipe.id, ))

        # user cannot request model schema of an item he doesn't have access to
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        response = self.client.get(url)
        self.assertApiResponse(response)

        self.assertIn("data", response.json())
        self.assertIn("feature", response.json().get("data"))
        self.assertContains(response, "petal_length")
        self.assertContains(response, "petal_width")
        self.assertContains(response, "sepal_length")
        self.assertContains(response, "sepal_width")

    def OFF_test_model_statistics(self):
        # recipe's automl config has never run before and the statistics don't exist
        recipe_automl_never_run = Recipe.objects.create(pk="rx_automl_config_never_run", workspace_id=self.ws1.id)
        recipe_automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:recipe-automl-statistics", args=(recipe_automl_never_run.id, ))
        response = self.client.get(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)

        # pre-generated artifacts are loaded in the `self.ws2` drive at:
        # //u206378@u206378.your-storagebox.de/user5-test/automl/rx_iris_unittest_artifacts/pipelines
        # URI to the artifacts are retrieved using `self.run_recipe_id` references in the mlmetadata-db.
        # In case of new runs of `self.run_recipe_id`'s automl pipeline, folder id in the above location 
        # must be changed accordingly.        
        recipe = Recipe.objects.create(pk=self.run_recipe_id, workspace_id=self.ws2.id)
        recipe.save()
        url = reverse("api:recipe-automl-statistics", args=(recipe.id, ))

        # user cannot request model statistics of an item he doesn't have access to
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        response = self.client.get(url)
        self.assertApiResponse(response)

        schema = response.json().get("data")
        self.assertIn("datasets", schema)
        self.assertEqual(1, len(schema["datasets"]))
        self.assertEqual("84", schema["datasets"][0]["numExamples"])

    def OFF_test_model_examples(self):
        # recipe's automl config has never run before and the examples don't exist
        recipe_automl_never_run = Recipe.objects.create(pk="rx_automl_config_never_run", workspace_id=self.ws1.id)
        recipe_automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:recipe-automl-statistics", args=(recipe_automl_never_run.id, ))
        response = self.client.get(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)


        # pre-generated artifacts are loaded in the `self.ws2` drive at:
        # //u206378@u206378.your-storagebox.de/user5-test/automl/rx_iris_unittest_artifacts/pipelines
        # URI to the artifacts are retrieved using `self.run_recipe_id` references in the mlmetadata-db.
        # In case of new runs of `self.run_recipe_id`'s automl pipeline, folder id in the above location 
        # must be changed accordingly.
        recipe = Recipe.objects.create(pk=self.run_recipe_id, workspace_id=self.ws2.id)
        recipe.set_attribute("automl", { "target_column": "variety" })
        recipe.save()
        url = reverse("api:recipe-automl-examples", args=(recipe.id, ))

        # user cannot request model examples of an item he doesn't have access to
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        response = self.client.get(url)
        self.assertApiResponse(response)

        data = response.json().get("data")
        self.assertIn("instances", data)
        self.assertIn("labels", data)

        instances = data.get("instances")
        self.assertEqual(10, len(instances))
        self.assertIn("petal_length", instances[0])
        self.assertIn("petal_width", instances[0])
        self.assertIn("sepal_length", instances[0])
        self.assertIn("sepal_width", instances[0])
        self.assertNotIn("variety", instances[0])

        labels = data.get("labels")
        self.assertEqual(10, len(labels))
        self.assertIn("variety", labels[0])