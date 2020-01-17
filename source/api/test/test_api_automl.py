import json
import requests
import time

from django.urls import reverse
from django.test import tag
from rest_framework import status

from api.models import *
from .utils import AnaliticoApiTestCase
from analitico.utilities import id_generator
from api.k8 import kubectl, K8_STAGE_PRODUCTION, K8_DEFAULT_NAMESPACE, k8_normalize_name, k8_wait_for_condition
from api.kubeflow import automl_convert_request_for_prediction, tensorflow_serving_deploy


class AutomlTests(AnaliticoApiTestCase):

    # id of the automl item already run on Kubeflow Pipeline to
    # use for testing artifacts or predictions
    run_automl_id = "au_test_automl_with_iris_labeled"

    def cleanup_deployed_resources(self, workspace_id):
        """ 
        Some actions (eg, the run of an automl config) also deploy Persistent Volume and TFServing service.
        The method simplifies the deletion of all services deployed by tests. 
        """
        try:
            kubectl(K8_DEFAULT_NAMESPACE, "delete", f"service/{k8_normalize_name(workspace_id)}-tfserving", output=None)
        except:
            pass
        try:
            kubectl(
                K8_DEFAULT_NAMESPACE,
                "delete",
                "pvc,pv",
                args=["--selector", "analitico.ai/workspace-id=" + workspace_id],
                output=None,
            )
        except:
            pass
        # TODO: cannot be cleaned because they are in used by kf pipeline executors' pods
        # try:
        #     kubectl(
        #         "kubeflow",
        #         "delete",
        #         "pvc,pv",
        #         args=["--selector", "analitico.ai/workspace-id=" + workspace_id],
        #         context_name="admin@cloud-staging.analitico.ai",
        #         output=None,
        #     )
        # except:
        #     pass

    def test_automl_run(self):
        try:
            # create a recipe with automl configs
            automl_id = "au_test_api_automl_test_run_and_tfserving_deploy"
            automl = Automl.objects.create(pk=automl_id, workspace_id=self.ws2.id)
            automl.set_attribute(
                "automl",
                {
                    "workspace_id": self.ws2.id,
                    "automl_id": automl_id,
                    "data_item_id": automl_id,
                    "data_path": "data",
                    "prediction_type": "regression",
                    "target_column": "target",
                },
            )
            automl.save()
            # upload dataset used by pipeline
            self.auth_token(self.token2)
            data_url = reverse("api:automl-files", args=(automl.id, "data/iris.csv"))
            self.upload_file(
                data_url,
                # TODO: files should be moved to automls/au_iris/..
                "../../../../automl/mount/automls/au_iris/data/iris.csv",
                content_type="text/csv",
                token=self.token1,
            )

            # user cannot run automl he doesn't have access to
            self.auth_token(self.token3)
            url = reverse("api:automl-run", args=(automl.id,))
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # without automl_config
            self.auth_token(self.token2)
            automl_without_automl_config = Automl.objects.create(
                pk="au_without_automl_config", workspace_id=self.ws2.id
            )
            url = reverse("api:automl-run", args=(automl_without_automl_config.id,))
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

            # user can run an automl config on an automl item he owns
            self.auth_token(self.token2)
            url = reverse("api:automl-run", args=(automl.id,))
            response = self.client.post(url)
            self.assertApiResponse(response)

            data = response.json().get("data")
            attributes = data["attributes"]

            # not yet started
            self.assertIn("automl", attributes)
            self.assertIsNotNone(attributes["automl"])
            # run id is saved in automl config
            automl.refresh_from_db()
            self.assertEqual(attributes["automl"]["run_id"], automl.get_attribute("automl.run_id"))

            # test tfserving endpoint and related expected resources
            self.assert_automl_run_deployed_persistent_volume_and_tfserving_endpoint(automl_id)
        finally:
            self.cleanup_deployed_resources(self.ws2.id)

    def assert_automl_run_deployed_persistent_volume_and_tfserving_endpoint(self, automl_id: str):
        """ 
        When is run an automl config expect to find deployed the Persistent Volume and
        Claim and the TFServing endpoint. 
        """
        try:
            # model run and loaded in:
            # //u206378.your-storagebox.de/automls/au_test_api_automl_test_run_and_tfserving_deploy/serving
            service_name = k8_normalize_name(self.ws2.id) + "-tfserving"

            # wait for pod to be scheduled
            time.sleep(3)
            k8_wait_for_condition(K8_DEFAULT_NAMESPACE, "pod", "condition=Ready", labels="app=" + service_name)

            # test endpoint
            url = (
                f"https://{k8_normalize_name(self.ws2.id)}-tfserving.cloud.analitico.ai/v1/models/au_test_api_automl_test_run_and_tfserving_deploy"
            )
            response = requests.get(url)
            self.assertApiResponse(response)

            # the run of an automl config also deploys Persistent Volume
            # and KFServing endpoint
            service, _ = kubectl(K8_DEFAULT_NAMESPACE, "get", f"service/{k8_normalize_name(self.ws2.id)}-tfserving") 
            self.assertIsNotNone(service)

            # persistent volume and claim are deployed with the serving endpoint
            response, _ = kubectl(
                K8_DEFAULT_NAMESPACE, "get", "pv", args=["--selector", "analitico.ai/workspace-id=" + self.ws2.id] )
            self.assertEqual(1, len(response["items"]))
            # persistent volume is bound to the right claim
            pv = response["items"][0]
            self.assertEqual("Bound", pv["status"]["phase"])
            self.assertEqual("analitico-drive-ws-002-claim", pv["spec"]["claimRef"]["name"])

            # persistent volume and claim are deployed also in the cloud-staging cluster
            # to be used for KFP execution
            # TODO: kfp runs should be deployed in `cloud` namespace instead of kubeflow
            response, _ = kubectl(
                "kubeflow",
                "get",
                "pv",
                args=["--selector", "analitico.ai/workspace-id=" + self.ws2.id], context_name="admin@cloud-staging.analitico.ai",
            )
            self.assertEqual(1, len(response["items"]))
            # persistent volume is bound to the right claim in the kubeflow namespace
            pv = response["items"][0]
            self.assertEqual("kubeflow", pv["spec"]["claimRef"]["namespace"])
        finally:
            self.cleanup_deployed_resources(self.ws2.id)

    def test_automl_convert_predict_request(self):
        # pre-generated artifacts are loaded in the `self.ws2` drive at:
        # //u206378.your-storagebox.de/user5-test/automls/au_test_automl_with_iris_labeled/pipelines
        # URI to the artifacts are retrieved using `self.run_automl_id` references in the mlmetadata-db.
        # In case of new runs of `self.run_automl_id`'s automl pipeline, folder id in the above location
        # must be changed accordingly.
        automl = Automl.objects.create(pk=self.run_automl_id, workspace_id=self.ws2.id)

        # single prediction
        content = automl_convert_request_for_prediction(
            automl, {"instances": [{"sepal_length": 6.4, "sepal_width": 2.8, "petal_length": 5.6, "petal_width": 2.2}]}
        )
        self.assertIsNotNone(content)
        content = json.loads(content)
        self.assertIn("instances", content)
        self.assertEqual(1, len(content["instances"]))
        self.assertIn("b64", content["instances"][0])
        self.assertTrue(content["instances"][0]["b64"])

        # multiple predictions
        content = automl_convert_request_for_prediction(
            automl,
            {
                "instances": [
                    {"sepal_length": 6.4, "sepal_width": 2.8, "petal_length": 5.6, "petal_width": 2.2},
                    {"sepal_length": 6.4, "sepal_width": 2.8, "petal_length": 5.6, "petal_width": 2.2},
                ]
            },
        )
        self.assertIsNotNone(content)
        content = json.loads(content)
        self.assertIn("instances", content)
        self.assertEqual(2, len(content["instances"]))
        self.assertIn("b64", content["instances"][0])
        self.assertTrue(content["instances"][0]["b64"])
        self.assertIn("b64", content["instances"][1])
        self.assertTrue(content["instances"][1]["b64"])

    # TODO: testalo con l'oggetto automl
    def OFF_test_predict(self):
        # recipe's automl config has never run before and the predict cannot be performed
        automl_never_run = Automl.objects.create(pk="au_automl_config_never_run", workspace_id=self.ws1.id) 
        automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:automl-predict", args=(automl_never_run.id,))
        response = self.client.post(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)

        # model for prediction is served from the workspace `ws_y1ehlz2e` drive
        url = f"https://api-staging.cloud.analitico.ai/api/automls/{self.run_automl_id}/predict"
        content = '{ "instances": [ {"sepal_length":6.4, "sepal_width":2.8, "petal_length":5.6, "petal_width":2.2} ] }'
        headers = {"Authorization": "Bearer tok_demo1_croJ7gVp4cW9", "Content-Type": "application/json"}

        # TODO: get_object() raises 404 not found
        # user can request prediction even without authentication
        # response = requests.post(url, data=content)
        # self.assertApiResponse(response)

        response = requests.post(url, data=content, headers=headers)
        self.assertApiResponse(response)

        predictions = response.json()
        self.assertIn("predictions", predictions)
        self.assertEqual(1, len(predictions))

        prediction = predictions["predictions"][0]
        self.assertIn("scores", prediction)
        self.assertEqual(prediction["scores"], [0.019_905_522_5, 0.980_042_815, 5.161_817_9e-05])
        self.assertEqual(prediction["classes"], ["Versicolor", "Virginica", "Setosa"])

    def test_model_schema(self):
        # automl config has never run before and the schema does not exist
        automl_never_run = Recipe.objects.create(pk="au_automl_config_never_run", workspace_id=self.ws2.id)
        automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:automl-schema", args=(automl_never_run.id,))
        response = self.client.get(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)

        # pre-generated artifacts are loaded in the `self.ws2` drive at:
        # //u206378.your-storagebox.de/user5-test/automls/au_test_automl_with_iris_labeled/pipelines
        # URI to the artifacts are retrieved using `self.run_automl_id` references in the mlmetadata-db.
        # In case of new runs of `self.run_automl_id`'s automl pipeline, folder id in the above location
        # must be changed accordingly.
        automl = Automl.objects.create(pk=self.run_automl_id, workspace_id=self.ws2.id)
        automl.save()
        url = reverse("api:automl-schema", args=(automl.id,))

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

    def test_model_statistics(self):
        # automl config has never run before and the statistics don't exist
        automl_never_run = Recipe.objects.create(pk="au_automl_config_never_run", workspace_id=self.ws1.id)
        automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:automl-statistics", args=(automl_never_run.id,))
        response = self.client.get(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)

        # pre-generated artifacts are loaded in the `self.ws2` drive at:
        # //u206378.your-storagebox.de/user5-test/automls/au_test_automl_with_iris_labeled/pipelines
        # URI to the artifacts are retrieved using `self.run_automl_id` references in the mlmetadata-db.
        # In case of new runs of `self.run_automl_id`'s automl pipeline, folder id in the above location
        # must be changed accordingly.
        automl = Automl.objects.create(pk=self.run_automl_id, workspace_id=self.ws2.id)
        automl.save()
        url = reverse("api:automl-statistics", args=(automl.id,))

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

    def test_model_examples(self):
        # automl config has never run before and the examples don't exist
        automl_never_run = Automl.objects.create(pk="au_automl_config_never_run", workspace_id=self.ws1.id)
        automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:automl-statistics", args=(automl_never_run.id,))
        response = self.client.get(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)

        # pre-generated artifacts are loaded in the `self.ws2` drive at:
        # //u206378.your-storagebox.de/user5-test/automls/au_test_automl_with_iris_labeled/pipelines
        # URI to the artifacts are retrieved using `self.run_automl_id` references in the mlmetadata-db.
        # In case of new runs of `self.run_automl_id`'s automl pipeline, folder id in the above location
        # must be changed accordingly.
        automl = Automl.objects.create(pk=self.run_automl_id, workspace_id=self.ws2.id)
        automl.set_attribute("automl", {"target_column": "variety"})
        automl.save()
        url = reverse("api:automl-examples", args=(automl.id,))

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

    
    def test_model_preconditioner_statistics(self):
        # automl config has never run before and the examples don't exist
        automl_never_run = Automl.objects.create(pk="au_automl_config_never_run", workspace_id=self.ws1.id)
        automl_never_run.save()
        self.auth_token(self.token1)
        url = reverse("api:automl-preconditioner", args=(automl_never_run.id,))
        response = self.client.get(url)
        self.assertApiResponse(response, status_code=status.HTTP_404_NOT_FOUND)

        # pre-generated artifacts are loaded in the `self.ws2` drive at:
        # //u206378.your-storagebox.de/user5-test/automls/au_test_automl_with_iris_labeled/pipelines
        # URI to the artifacts are retrieved using `self.run_automl_id` references in the mlmetadata-db.
        # In case of new runs of `self.run_automl_id`'s automl pipeline, folder id in the above location
        # must be changed accordingly.
        automl = Automl.objects.create(pk=self.run_automl_id, workspace_id=self.ws2.id)
        automl.save()
        url = reverse("api:automl-preconditioner", args=(automl.id,))

        # user cannot request model examples of an item he doesn't have access to
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        response = self.client.get(url)
        self.assertApiResponse(response)

        data = response.json().get("data")
        self.assertGreater(data["count"] , 0)
        self.assertIn("features", data)
        
        features = data["features"]
        self.assertIn("variety", features)
        self.assertEqual(features["variety"]["dtype"], "object")
        self.assertEqual(features["variety"]["name"], "variety")
        self.assertIn("Setosa", features["variety"]["values"])
        self.assertGreater(features["variety"]["values"]["Setosa"], 0)
