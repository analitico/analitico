import time
import json
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
        """ """
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

    @tag("k8s", "kf")
    def OFF_test_kf_pipeline_runs(self):
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

    @tag("k8s", "kf", "live")
    def OFF_test_kf_serving_deploy(self):
        """ Deploy a TensorFlow model with Knative """
        service_name = None
        try:
            # artifact loaded in
            # //u212674.your-storagebox.de/ws_y1ehlz2e/automl/rx_testk8_test_kf_serving_deploy/serving
            recipe_id = "rx_testk8_test_kf_serving_deploy"
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

            self.auth_token(self.token1)
            url = reverse("api:recipe-k8-deploy", args=(recipe_id, K8_STAGE_STAGING))
            response = self.client.post(url)
            self.assertApiResponse(response)

            data = response.json().get("data")
            service_name = data.get("name")

            # wait for pod to be scheduled
            time.sleep(3)
            k8_wait_for_condition(
                K8_DEFAULT_NAMESPACE,
                "pod",
                "condition=Ready",
                labels="serving.kubeflow.org/inferenceservice=" + service_name,
            )

            # retrieve service information from kubernetes cluster
            service, _ = kubectl(K8_DEFAULT_NAMESPACE, "get", "inferenceService/" + service_name)

            self.assertEquals(service["apiVersion"], "serving.kubeflow.org/v1alpha2")
            self.assertEquals(service["kind"], "InferenceService")
            self.assertIn("metadata", service)
            self.assertIn("spec", service)
            self.assertIn("status", service)
        finally:
            if service_name:
                kubectl(K8_DEFAULT_NAMESPACE, "delete", "inferenceService/" + service_name, output=None)

    def test_kf_update_tensorflow_model_config(self):
        recipe = Recipe.objects.create(pk="rx_automl_model_config", workspace=self.ws1)
        recipe.save()

        kf_update_tensorflow_model_config(recipe)
