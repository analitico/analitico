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
    def kf_run_pipeline(self, automl_id: str = None) -> dict:
        """ Execute an Automl pipeline for testing and return the Analitico model as json. """
        if not automl_id:
            automl_id = "au_test_iris"

        # create an automl item with automl configs
        automl, isNew = Automl.objects.get_or_create(pk=automl_id, workspace_id=self.ws1.id)
        automl.set_attribute(
            "automl",
            {
                "workspace_id": "ws_001",
                "automl_id": automl_id,
                "data_item_id": "au_iris",
                "data_path": "data",
                "prediction_type": "regression",
                "target_column": "target",
            },
        )
        automl.save()
        # upload dataset used by pipeline
        self.auth_token(self.token1)
        data_url = url = reverse("api:automl-files", args=(automl.id, "data/iris.csv"))
        self.upload_file(
            data_url,
            "../../../../automl/mount/automls/au_iris/data/iris.csv",
            content_type="text/csv",
            token=self.token1,
        )

        url = reverse("api:automl-run", args=(automl_id,))
        self.auth_token(self.token1)
        response = self.client.post(url)
        self.assertApiResponse(response)

        return response.json().get("data")

    def cleanup_kf_test_services(self):
        """ 
        Some actions (eg, the run of an automl config) also deploy Persistent Volume and TFServing service.
        The method simplifies the deletion of all services deployed by tests. 
        """
        try:
            kubectl(
                K8_DEFAULT_NAMESPACE,
                "delete",
                "service",
                args=["--selector", "analitico.ai/service=tfserving,analitico.ai/workspace-id=" + self.ws1.id],
                output=None,
            )
        except:
            pass
        try:
            kubectl(
                K8_DEFAULT_NAMESPACE,
                "delete",
                "pvc,pv",
                args=["--selector", "analitico.ai/workspace-id=" + self.ws1.id],
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
        #         args=["--selector", "analitico.ai/workspace-id=" + self.ws1.id],
        #         context_name="admin@cloud-staging.analitico.ai",
        #         output=None,
        #     )
        # except:
        #     pass

    ##
    ## Test Kubeflow
    ##

    @tag("k8s", "kf", "slow")
    def test_kf_pipeline_runs(self):
        try:
            """ Test Kubeflow get and list pipeline run objects """
            # run a pipeline for testing
            content = self.kf_run_pipeline()
            automl_id = get_dict_dot(content, "attributes.automl_id")
            run_id = get_dict_dot(content, "attributes.automl.run_id")
            experiment_id = get_dict_dot(content, "attributes.automl.experiment_id")

            # user cannot retrieve runs if he doesn't have access
            # to the related analitico item
            self.auth_token(self.token2)
            url = reverse("api:automl-kf-pipeline-runs", args=(automl_id, run_id))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # automl not found
            self.auth_token(self.token1)
            url = reverse("api:automl-kf-pipeline-runs", args=("au_fake_id", run_id))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # run id not found
            self.auth_token(self.token1)
            url = reverse("api:automl-kf-pipeline-runs", args=(automl_id, "fake-run-id"))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # retrieve the specific run
            self.auth_token(self.token1)
            url = reverse("api:automl-kf-pipeline-runs", args=(automl_id, run_id))
            response = self.client.get(url)
            self.assertApiResponse(response)
            data = response.json()
            self.assertEqual(data["data"]["run"]["id"], run_id)

            # user cannot retrieve pipeline ran in an experiment
            # not releated to the given item id.
            # Create a new Automl and replace the experiment id
            # from the other run
            invalid_automl_id = "au_test_runs"
            self.kf_run_pipeline(invalid_automl_id)
            invalid_automl = Automl.objects.get(pk=invalid_automl_id)
            invalid_automl.set_attribute("automl.experiment_id", experiment_id)
            invalid_automl.save()

            self.auth_token(self.token1)
            url = reverse("api:automl-kf-pipeline-runs", args=(invalid_automl_id, ""))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # retrieve the list of runs for a given item id
            self.auth_token(self.token1)
            url = reverse("api:automl-kf-pipeline-runs", args=(automl_id, ""))
            response = self.client.get(url)
            self.assertApiResponse(response)
            data = response.json().get("data")
            self.assertGreaterEqual(len(data["runs"]), 1)
        finally:
            self.cleanup_kf_test_services()

    @tag("k8s", "slow")
    def test_automl_run_also_deploys_persistent_volume_and_tfserving_endpoint(self):
        """ 
        When is run an automl config expect to find deployed the Persistent Volume and
        Claim and the TFServing endpoint. 
        """
        try:     
            # model pre-loaded in
            # //u212674.your-storagebox.de/ws_y1ehlz2e/automl/au_testk8_test_tensorflow_serving_deploy/serving
            automl_id = "au_testk8_test_tensorflow_serving_deploy"            
            # run a recipe in the `self.ws1` workspace
            self.kf_run_pipeline(automl_id=automl_id)
            service_name = k8_normalize_name(self.ws1.id) + "-tfserving"

            # wait for pod to be scheduled
            time.sleep(3)
            k8_wait_for_condition(K8_DEFAULT_NAMESPACE, "pod", "condition=Ready", labels="app=" + service_name)

            # test endpoint
            url = "https://ws-001-tfserving.cloud.analitico.ai/v1/models/au_testk8_test_tensorflow_serving_deploy"
            response = requests.get(url)
            self.assertApiResponse(response)

            # a next deploy should not change any deployed services
            # and thus everything should complete fine.
            self.kf_run_pipeline(automl_id=automl_id)

            # the run of an automl config also deploys Persistent Volume
            # and KFServing endpoint
            service, _ = kubectl(K8_DEFAULT_NAMESPACE, "get", f"service/{k8_normalize_name(self.ws1.id)}-tfserving")
            self.assertIsNotNone(service)

            # persistent volume and claim are deployed with the serving endpoint
            response, _ = kubectl(
                K8_DEFAULT_NAMESPACE, "get", "pv", args=["--selector", "analitico.ai/workspace-id=" + self.ws1.id]
            )
            self.assertEqual(1, len(response["items"]))
            # persistent volume is bound to the right claim
            pv = response["items"][0]
            self.assertEqual("Bound", pv["status"]["phase"])
            self.assertEqual("analitico-drive-ws-001-claim", pv["spec"]["claimRef"]["name"])

            # persistent volume and claim are deployed also in the cloud-staging cluster
            # to be used for KFP execution
            # TODO: kfp runs should be deployed in `cloud` namespace instead of kubeflow
            response, _ = kubectl(
                "kubeflow",
                "get",
                "pv",
                args=["--selector", "analitico.ai/workspace-id=" + self.ws1.id],
                context_name="admin@cloud-staging.analitico.ai",
            )
            self.assertEqual(1, len(response["items"]))
            # persistent volume is bound to the right claim in the kubeflow namespace
            pv = response["items"][0]
            self.assertEqual("kubeflow", pv["spec"]["claimRef"]["namespace"])
        finally:
            self.cleanup_kf_test_services()

    def test_kf_update_tensorflow_models_config(self):
        # update model config from empty config
        automl = Automl.objects.create(pk="au_automl_model_config", workspace=self.ws1)
        automl.save()

        config = kf_update_tensorflow_models_config(automl, "")
        self.assertIn('name: "au_automl_model_config"', config)
        self.assertIn('base_path: "/mnt/automl/au_automl_model_config/serving"', config)
        self.assertIn('model_platform: "tensorflow"', config)

        # update model config from empty config
        automl2 = Automl.objects.create(pk="au_automl_model_config_2", workspace=self.ws1)
        automl2.save()

        config = kf_update_tensorflow_models_config(automl2, config)
        self.assertIn('name: "au_automl_model_config_2"', config)
        self.assertIn('base_path: "/mnt/automl/au_automl_model_config_2/serving"', config)
        self.assertIn('model_platform: "tensorflow"', config)

        # update model config from an existing config, re-add an existing item's model
        config = kf_update_tensorflow_models_config(automl2, config)
        self.assertEqual(config.count('name: "au_automl_model_config_2"'), 1, "model should not be present twice")
        self.assertEqual(
            config.count('base_path: "/mnt/automl/au_automl_model_config_2/serving'),
            1,
            "model should not be present twice",
        )
