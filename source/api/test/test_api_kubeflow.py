import time
import json
import requests
from django.urls import reverse

from rest_framework import status
from django.test import tag
from django.urls import reverse

from api.models import *
from .utils import AnaliticoApiTestCase
from api.kubeflow import *
from api.k8 import kubectl, k8_wait_for_condition, K8_DEFAULT_NAMESPACE


class KubeflowTests(AnaliticoApiTestCase):
    def kf_run_pipeline(self, recipe_id: str = None) -> Model:
        """ Execute an Automl pipeline for testing """
        if not recipe_id:
            recipe_id = "rx_test_iris"

        # create a recipe with automl configs
        recipe = Recipe.objects.create(pk=recipe_id, workspace_id=self.ws1.id)
        recipe.set_attribute(
            "automl",
            {
                "workspace_id": "ws_001",
                "recipe_id": recipe_id,
                "data_item_id": "rx_iris",
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

        return automl_run(recipe)

    ##
    ## Test Kubeflow
    ##

    @tag("k8s", "kf", "slow")
    def test_kf_pipeline_runs(self):
        """ Test Kubeflow get and list pipeline run objects """ 
        # run a pipeline for testing
        model = self.kf_run_pipeline()
        recipe_id = model.get_attribute("recipe_id")
        run_id = model.get_attribute("automl.run_id")

        # user cannot retrieve runs if he doesn't have access
        # to the related analitico item
        self.auth_token(self.token2)
        url = reverse("api:recipe-kf-pipeline-runs", args=(recipe_id, run_id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        url = reverse("api:recipe-kf-pipeline-runs", args=("rx_fake_id", run_id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # retrieve the specific run
        self.auth_token(self.token1)
        url = reverse("api:recipe-kf-pipeline-runs", args=(recipe_id, run_id))
        response = self.client.get(url)
        self.assertApiResponse(response)
        data = response.json()
        self.assertEqual(data["data"]["run"]["id"], run_id)

        # user cannot retrieve pipeline ran in an experiment
        # not releated to the given item id.
        # Create a new recipe and replace the experiment id
        # from the other run
        invalid_recipe_id = "rx_test_runs"
        self.kf_run_pipeline(invalid_recipe_id)
        invalid_recipe = Recipe.objects.get(pk=invalid_recipe_id)
        invalid_recipe.set_attribute("automl.experiment_id", model.get_attribute("automl.experiment_id"))
        invalid_recipe.save()

        self.auth_token(self.token1)
        url = reverse("api:recipe-kf-pipeline-runs", args=(invalid_recipe_id, ""))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # retrieve the list of runs for a given item id
        self.auth_token(self.token1)
        url = reverse("api:recipe-kf-pipeline-runs", args=(recipe_id, ""))
        response = self.client.get(url)
        self.assertApiResponse(response)
        data = response.json().get("data")
        self.assertGreaterEqual(len(data["runs"]), 1)

    @tag("k8s", "kf", "live", "slow")
    def test_tensorflow_serving_deploy(self):
        """ Test deploy of a TensorFlow model with Knative """
        try:
            # artifact loaded in
            # //u212674.your-storagebox.de/ws_y1ehlz2e/automl/rx_testk8_test_tensorflow_serving_deploy/serving
            recipe_id = "rx_testk8_test_tensorflow_serving_deploy"
            recipe = Recipe.objects.create(pk=recipe_id, workspace=self.ws1)
            recipe.set_attribute(
                "automl",
                {
                    "workspace_id": "ws_y1ehlz2e",
                    "recipe_id": recipe_id,
                    "data_item_id": "rx_iris",
                    "data_path": "data",
                    "prediction_type": "regression",
                    "target_column": "target",
                },
            )
            recipe.save()

            model = Model.objects.create(pk="ml_testk8_test_tensorflow_serving_deploy", workspace=self.ws1)
            model.save()
            result = tensorflow_serving_deploy(recipe, model)

            service_name = result.get("name")

            # wait for pod to be scheduled
            time.sleep(3)
            k8_wait_for_condition(
                K8_DEFAULT_NAMESPACE,
                "pod",
                "condition=Ready",
                labels="app=" + service_name,
            )

            # test endpoint
            url = "https://ws-001.cloud.analitico.ai/v1/models/rx_testk8_test_tensorflow_serving_deploy"
            # url = "https://ws-001.cloud.cloud-staging.analitico.ai/v1/models/rx_testk8_test_tensorflow_serving_deploy"
            response = requests.get(url)
            # response = requests.get(url, verify=False)
            self.assertApiResponse(response)
        finally:
            try:
                kubectl(K8_DEFAULT_NAMESPACE, "delete", "service/" + service_name, output=None)
            except:
                pass

    def test_kf_update_tensorflow_models_config(self):
        # from empty config
        recipe = Recipe.objects.create(pk="rx_automl_model_config", workspace=self.ws1)
        recipe.save()

        config = kf_update_tensorflow_models_config(recipe, "")
        self.assertIn('name: "rx_automl_model_config"', config)
        self.assertIn('base_path: "/mnt/automl/rx_automl_model_config/serving"', config)
        self.assertIn('model_platform: "tensorflow"', config)

        # from an existing config
        recipe2 = Recipe.objects.create(pk="rx_automl_model_config_2", workspace=self.ws1)
        recipe2.save()

        config = kf_update_tensorflow_models_config(recipe2, config)
        self.assertIn('name: "rx_automl_model_config_2"', config)
        self.assertIn('base_path: "/mnt/automl/rx_automl_model_config_2/serving"', config)
        self.assertIn('model_platform: "tensorflow"', config)

        # from an existing config re-add an existing item's model
        config = kf_update_tensorflow_models_config(recipe2, config)
        self.assertEqual(config.count('name: "rx_automl_model_config_2"'), 1, "model should not be present twice")
        self.assertEqual(config.count('base_path: "/mnt/automl/rx_automl_model_config_2/serving'), 1, "model should not be present twice")
