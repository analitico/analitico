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
from analitico.utilities import get_dict_dot


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
                "workspace_id": self.ws1.id,
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
            self.cleanup_deployed_resources(self.ws1.id)

    def test_kf_update_tensorflow_models_config(self):
        # update model config from empty config
        automl = Automl.objects.create(pk="au_automl_model_config", workspace=self.ws1)
        automl.save()

        config = tensorflow_models_config_update(automl, "")
        self.assertIn('name: "au_automl_model_config"', config)
        self.assertIn('base_path: "/mnt/automls/au_automl_model_config/serving"', config)
        self.assertIn('model_platform: "tensorflow"', config)

        # update model config from empty config
        automl2 = Automl.objects.create(pk="au_automl_model_config_2", workspace=self.ws1)
        automl2.save()

        config = tensorflow_models_config_update(automl2, config)
        self.assertIn('name: "au_automl_model_config_2"', config)
        self.assertIn('base_path: "/mnt/automls/au_automl_model_config_2/serving"', config)
        self.assertIn('model_platform: "tensorflow"', config)

        # update model config from an existing config, re-add an existing item's model
        config = tensorflow_models_config_update(automl2, config)
        self.assertEqual(config.count('name: "au_automl_model_config_2"'), 1, "model should not be present twice")
        self.assertEqual(
            config.count('base_path: "/mnt/automls/au_automl_model_config_2/serving'),
            1,
            "model should not be present twice",
        )

    def test_tesorflow_job_deploy_and_get(self):
        tfjob_id = None
        try:
            automl = Automl.objects.create(pk="au_tfjob", workspace=self.ws1)
            automl.save()
            url = reverse("api:automl-tfjob-deploy", args=(automl.id, ))
            trainer_config = {"data": {"just-a-key": 3}}
            
            # only admin can request a tfjob
            self.auth_token(self.token2)
            response = self.client.post(url, data=trainer_config, format="json")
            self.assertApiResponse(response, status_code=status.HTTP_403_FORBIDDEN)

            # missing trainer config
            self.auth_token(self.token1)
            response = self.client.post(url, data={}, format="json")
            self.assertApiResponse(response, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # tfjob is deployed with the expected trainer config
            self.auth_token(self.token1)
            response = self.client.post(url, data=trainer_config, format="json")
            self.assertApiResponse(response)
            
            # trainer config has been set in the arguments for the image's command
            tfjob = response.json().get("data", {})
            tfjob_id = get_dict_dot(tfjob, "metadata.name")
            self.assertIsNotNone(tfjob_id)
            container = get_dict_dot(tfjob, "spec.tfReplicaSpecs.Worker.template.spec.containers")[0]
            self.assertIn("just-a-key", container["args"][1])

            url = reverse("api:automl-tfjob-get", args=(automl.id, tfjob_id, ))
            # only admin get retrieve the status of a tfjob
            self.auth_token(self.token2)
            response = self.client.get(url)
            self.assertApiResponse(response, status_code=status.HTTP_403_FORBIDDEN)

            # retrieve the status
            self.auth_token(self.token1)
            response = self.client.get(url)
            self.assertApiResponse(response)
            tfjob = response.json().get("data", {})
            actual_tfjob_id = get_dict_dot(tfjob, "metadata.name")
            self.assertEqual(tfjob_id, actual_tfjob_id)
        finally:
            if tfjob_id:
                kubectl("kubeflow", "delete", "tfjob/" + tfjob_id, context_name="admin@cloud-staging.analitico.ai", output=None)

