import os
import os.path
import json
import time
import requests
import dateutil.parser
from datetime import datetime

from django.test import tag
from django.urls import reverse
from rest_framework import status

# conflicts with django's dynamically generated model.objects

# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

from analitico.constants import ACTION_PROCESS, ACTION_DEPLOY
from analitico.utilities import read_json, subprocess_run, size_to_bytes

import api

from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *
from api.k8 import *

from .utils import AnaliticoApiTestCase

import logging

logger = logging.getLogger("analitico")


class K8Tests(AnaliticoApiTestCase):
    """ Test kubernets API to build and deploy on knative """

    stage = api.k8.K8_STAGE_STAGING
    item_id = "nb_K8Tests_test_k8"  # help registry cleanups
    item_id_normalized = "nb-k8tests-test-k8-staging"

    def deploy_service(self, wait=True):
        self.auth_token(self.token1)
        self.post_notebook("notebook11.ipynb", self.item_id)
        notebook = Notebook.objects.get(pk=self.item_id)
        # pre run and built image tagged with `K8Tests_test_k8_deploy`
        notebook.set_attribute(
            "docker",
            {
                "type": "analitico/docker",
                "image": "eu.gcr.io/analitico-api/rx-qx1ek6jb:ml-81anpwk3",
                "image_name": "eu.gcr.io/analitico-api/rx-qx1ek6jb:ml-81anpwk3",
                "image_id": "sha256:ff32d10b2b5b2e9577c1e1de90aeb200acc8a5ad161be58b5e4ca81f740e4d49",
            },
        )
        notebook.save()

        service = k8_deploy_v2(notebook, notebook, self.stage)
        self.assertEquals(service["type"], "analitico/service")
        self.assertEquals(service["name"], self.item_id_normalized)
        self.assertEquals(service["namespace"], "cloud")
        self.assertIn("url", service)

        if wait:
            k8_wait_for_condition(
                K8_DEFAULT_NAMESPACE, "pod", "condition=Ready", labels=f"serving.knative.dev/service=" + service["name"]
            )
        return service

    def deploy_jupyter(self, jupyter_name: str = None, custom_settings: dict = None) -> dict:

        self.auth_token(self.token1)
        if jupyter_name:
            # update existing jupyter configuration
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            response = self.client.put(url, data=custom_settings, format="json")
        else:
            # deploy a new jupyter
            url = reverse("api:workspace-k8-jupyter-deploy", args=(self.ws1.id,))
            response = self.client.post(url, data=custom_settings, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        return response.json().get("data")

    def job_run_notebook(self, item_id=None) -> (str, dict):
        if item_id is None:
            item_id = self.item_id
        self.post_notebook("notebook11.ipynb", item_id)
        notebook = Notebook.objects.get(pk=item_id)

        url_job_run = reverse("api:notebook-k8-jobs", args=(notebook.id, analitico.ACTION_RUN))
        response = self.client.post(url_job_run)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        job_id = response.data["metadata"]["name"]

        # wait for deployment
        time.sleep(15)

        return job_id, response.data

    @tag("slow", "docker", "k8s")
    def test_k8_deploy_docker(self):
        """ Test building a docker from a notebook then deploying it """

        self.deploy_service()

        # retrieve service information from kubernetes cluster
        service, _ = subprocess_run(
            cmd_args=[
                "kubectl",
                "get",
                "ksvc",
                self.item_id_normalized,
                "-n",
                api.k8.K8_DEFAULT_NAMESPACE,
                "-o",
                "json",
            ]
        )
        self.assertEquals(service["apiVersion"], "serving.knative.dev/v1alpha1")
        self.assertEquals(service["kind"], "Service")
        self.assertIn("metadata", service)
        self.assertIn("spec", service)
        self.assertIn("status", service)

    ##
    ## K8s APIs that work on ENTIRE cluster
    ##

    # we need to setup the credentials for kubectl in gitlab CI/CD
    @tag("k8s")
    def test_k8s_get_nodes(self):
        url = reverse("api:k8-nodes")

        # regular user CANNOT get nodes
        self.auth_token(self.token3)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # admin user CAN get nodes
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # should have at least one node running
        nodes = response.data["items"]
        self.assertGreaterEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["apiVersion"], "v1")
        self.assertEqual(nodes[0]["kind"], "Node")
        self.assertIn("metadata", nodes[0])
        self.assertIn("spec", nodes[0])
        self.assertIn("status", nodes[0])

    ##
    ## K8s APIs that work on specific service
    ##

    @tag("slow", "docker", "k8s")
    def test_serverless_cors_header(self):
        """ 
        Test CORS headers on a serverless endpoint 
        If the serverless image changes, deploy a new model of this recipe.
        """

        # serverless url
        url = "https://rx-qx1ek6jb-staging.cloud.analitico.ai"

        # check CORS headers for the OPTIONS method
        response = requests.options(
            url,
            headers={
                "Origin": "https://sample.com",
                "Referer": "https://sample.com/",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertStatusCode(response)
        self.assertIn("GET", response.headers.get("access-control-allow-methods"))
        self.assertIn("HEAD", response.headers.get("access-control-allow-methods"))
        self.assertIn("OPTIONS", response.headers.get("access-control-allow-methods"))
        self.assertIn("POST", response.headers.get("access-control-allow-methods"))
        self.assertIn("DELETE", response.headers.get("access-control-allow-methods"))
        self.assertEqual("https://sample.com", response.headers.get("access-control-allow-origin"))
        self.assertEqual("content-type", response.headers.get("access-control-allow-headers"))

        response = requests.post(
            url, data="{}", headers={"Origin": "https://sample.com", "Content-Type": "application/json;charset=utf-8"}
        )
        self.assertStatusCode(response)
        self.assertEqual("https://sample.com", response.headers.get("access-control-allow-origin"))

    @tag("k8s", "slow")
    def test_get_service_not_deployed(self):
        """ Test get the kservice for a stage not deployed returns not found """
        # it deploys in K8_STAGE_STAGING
        self.deploy_service()

        # ask for K8_STAGE_PRODUCTION
        url = reverse("api:notebook-k8-ksvc", args=(self.item_id, K8_STAGE_PRODUCTION))
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @tag("k8s", "slow")
    def test_get_revisions(self):
        """ Test list of revision for a specific stage """
        self.deploy_service()

        url = reverse("api:notebook-k8-revisions", args=(self.item_id, K8_STAGE_STAGING))

        # user CANNOT read logs from items he does not have access to
        self.auth_token(self.token3)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertGreaterEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["kind"], "Revision")
        self.assertIn(self.item_id_normalized, response.data["items"][0]["metadata"]["name"])

    @tag("slow", "k8s")
    def test_service_metrics(self):
        self.deploy_service()
        url = reverse("api:notebook-k8-metrics", args=(self.item_id, self.stage))

        # regular user CANNOT get metrics
        self.auth_token(self.token3)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # request fails empty metric
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        # request fails invalid metric
        self.auth_token(self.token1)
        response = self.client.get(url, data={"metric": "this-metric-does-not-exist"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        # without end time the request returns a single point of time
        self.auth_token(self.token1)
        response = self.client.get(url, data={"metric": "container_cpu_load", "start": int(time.time())}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["data"]["resultType"], "vector")

        # service not found in production
        self.auth_token(self.token2)
        url_production = reverse("api:notebook-k8-metrics", args=(self.item_id, api.k8.K8_STAGE_PRODUCTION))
        response = self.client.get(url_production, data={"metric": "container_cpu_load"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # admin user CAN get metrics
        self.auth_token(self.token1)
        response = self.client.get(url, data={"metric": "container_cpu_load"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # expect requested metric from specific service
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["data"]["result"]), 1)  # one per revision (if any)
        for metric in data["data"]["result"]:
            self.assertIn(self.item_id_normalized, metric["metric"]["pod_name"])

        # filter a specific metric over a specific time range
        now = int(time.time())
        thirtyMinutesAgo = now - (30 * 60)
        response = self.client.get(
            url,
            data={"metric": "container_cpu_load", "start": thirtyMinutesAgo, "end": now, "step": "1m"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["resultType"], "matrix")
        for metric in data["data"]["result"]:
            self.assertIn(self.item_id_normalized, metric["metric"]["pod_name"])

    @tag("slow", "k8s", "live")
    def test_service_logs(self):
        self.deploy_service()
        url = reverse("api:notebook-k8-logs", args=(self.item_id, self.stage))

        # /echo endpoint will generate a log message at the given level
        endpoint_echo = f"https://{self.item_id_normalized}.cloud.analitico.ai/echo"

        # generate info logs
        for x in range(20):
            response = requests.get(
                endpoint_echo, params={"message": f"INFO log for unit-testing", "level": logging.INFO}, verify=False
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # user CANNOT read logs from items he does not have access to
        self.auth_token(self.token3)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # admin user CAN get logs
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertGreater(len(data["hits"]["hits"]), 10)
        self.assertEqual(data["timed_out"], False)
        self.assertGreater(data["hits"]["total"], 10)

        # service not found in production
        self.auth_token(self.token2)
        url_production = reverse("api:notebook-k8-logs", args=(self.item_id, api.k8.K8_STAGE_PRODUCTION))
        response = self.client.get(url_production, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # limit the number of results with ?size= parameter
        self.auth_token(self.token1)
        response = self.client.get(url, data={"size": 10, "order": "@timestamp:desc"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(len(data["hits"]["hits"]), 10)
        self.assertEqual(data["timed_out"], False)
        self.assertGreater(data["hits"]["total"], 10)

        # user can provide a query string
        self.auth_token(self.token1)
        response = self.client.get(
            url, data={"query": '"this-is-a-string-that-will-never-be-present-in-a-log"'}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(len(data["hits"]["hits"]), 0)

        # search for error only
        self.auth_token(self.token1)
        response = self.client.get(url, data={"query": "level:info"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertGreater(len(data["hits"]["hits"]), 10)
        for d in data["hits"]["hits"]:
            self.assertEqual("info", d["_source"]["level"])

        # call the endpoint on k8 to generate each level log message and
        # track the time between logging and indexing in Elastic Search
        start_time = time.time()
        levels = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        message = f"test_k8s_get_logs-{start_time}"
        for level, level_number in levels.items():
            response = requests.get(
                endpoint_echo, params={"message": f"{message}-{level}", "level": level_number}, verify=False
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # wait for all logs to be indexed
        expected_results = len(levels)
        insist = True
        while insist:
            response = self.client.get(url, data={"query": f'msg:"{message}"', "size": expected_results})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            elapsed = round(time.time() - start_time, 2)
            if len(response.data["hits"]["hits"]) == expected_results:
                insist = False
                logging.log(logging.INFO, msg=f"Logs indexed in {elapsed} secs")
            else:
                time.sleep(2)
                insist = elapsed <= 60

        # check results from Elastic Search
        hits_len = len(response.data["hits"]["hits"])
        hits_total = response.data["hits"]["total"]
        self.assertEqual(hits_len, expected_results)
        self.assertEqual(hits_total, hits_len, f"Duplicated logs found. Retrieved {hits_len} but found {hits_total}.")

        for result in response.data["hits"]["hits"]:
            self.assertIn(result["_source"]["level"], levels.keys())
            del levels[result["_source"]["level"]]
            self.assertIn(message, result["_source"]["msg"])

    ##
    ## K8s Jobs
    ##

    @tag("k8s")
    def test_k8s_list_jobs_by_workspace(self):
        try:
            # post a job by running a notebook
            job_id, _ = self.job_run_notebook()

            url = reverse("api:workspace-k8-jobs", args=(self.ws1.id, ""))

            # user without permission cannot retrieve the list
            self.auth_token(self.token3)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            self.auth_token(self.token1)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertGreaterEqual(len(response.data["items"]), 1)

            # last job should be for our notebook
            lastJob = len(response.data["items"]) - 1
            lastJobItemId = response.data["items"][lastJob]["metadata"]["labels"]["analitico.ai/item-id"]
            self.assertEqual(lastJobItemId, self.item_id)
        finally:
            # clean up
            k8_job_delete(job_id)

    @tag("k8s")
    def test_get_specific_k8s_job_by_workspace(self):
        try:
            # post a job by running a notebook
            job_id, _ = self.job_run_notebook()

            url = reverse("api:workspace-k8-jobs", args=(self.ws1.id, job_id))

            # user without permission cannot retrieve the list
            self.auth_token(self.token3)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            self.auth_token(self.token1)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["metadata"]["labels"]["analitico.ai/item-id"], self.item_id)
        finally:
            # clean up
            k8_job_delete(job_id)

    @tag("slow", "k8s", "live")
    def test_k8s_job_logs(self):
        try:
            # run a job to generate logs
            job_id, _ = self.job_run_notebook()
            # wait for logs to be collected
            time.sleep(30)

            url = reverse("api:notebook-k8-job-logs", args=(self.item_id, job_id))

            # user CANNOT read logs from items he does not have access to
            self.auth_token(self.token3)
            response = self.client.get(url, format="json")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # user CANNOT read logs from jobs that does not belong to the item
            self.auth_token(self.token1)
            another_job_id, _ = self.job_run_notebook("nb_anothernotebook")
            another_job_url = reverse("api:notebook-k8-job-logs", args=(self.item_id, another_job_id))
            response = self.client.get(another_job_url, format="json")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # admin user CAN get logs
            self.auth_token(self.token1)
            response = self.client.get(url, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data
            self.assertGreater(len(data["hits"]["hits"]), 5)
            self.assertEqual(data["timed_out"], False)
            self.assertGreater(data["hits"]["total"], 5)

            # limit the number of results with ?size= parameter
            self.auth_token(self.token1)
            response = self.client.get(url, data={"size": 3, "order": "@timestamp:desc"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data
            self.assertEqual(len(data["hits"]["hits"]), 3)
            self.assertEqual(data["timed_out"], False)
            self.assertGreater(data["hits"]["total"], 3)

            # user can provide a query string
            self.auth_token(self.token1)
            response = self.client.get(
                url, data={"query": '"this-is-a-string-that-will-never-be-present-in-a-log"'}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data
            self.assertEqual(len(data["hits"]["hits"]), 0)
        finally:
            # clean up
            k8_job_delete(job_id)
            k8_job_delete(another_job_id)

    @tag("slow", "k8s", "live")
    def test_k8s_job_logs_from_workspace_item(self):
        """ Test retrieves job's logs from a workspace item """
        try:
            # post a job by running a notebook
            job_id, _ = self.job_run_notebook()

            url = reverse("api:workspace-k8-job-logs", args=(self.ws1.id, job_id))

            # user CANNOT read logs from items he does not have access to
            self.auth_token(self.token3)
            response = self.client.get(url, format="json")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # user CANNOT read logs from jobs that does not belong to the item
            self.auth_token(self.token1)
            another_workspace_url = reverse("api:notebook-k8-job-logs", args=(self.ws2.id, job_id))
            response = self.client.get(another_workspace_url, format="json")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # admin user CAN get logs
            self.auth_token(self.token1)
            response = self.client.get(url, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        finally:
            # clean up
            k8_job_delete(job_id)

    @tag("slow", "k8s", "live")
    def test_k8s_jobs_run(self):
        try:
            # required utc timestamp for date comparison
            test_start_time = datetime.utcnow().timestamp()

            # named: K8Tests.test_k8s_jobs_run
            receipe_id = "rx_x5b1npmn"
            notebook_name = "notebook.ipynb"
            server = "https://staging.analitico.ai"
            headers = {"Authorization": "Bearer tok_demo1_croJ7gVp4cW9", "Content-Type": "application/json"}

            # run the recipe
            url = reverse("api:recipe-k8-jobs", args=(receipe_id, analitico.ACTION_RUN))
            response = requests.post(
                server + url, data=json.dumps({"data": {"notebook": notebook_name}}), headers=headers
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            content = response.json()
            job_id = content["data"]["metadata"]["name"]
            url = reverse("api:recipe-k8-jobs", args=(receipe_id, job_id))

            # wait to complete
            insist = True
            while insist:
                response = requests.get(server + url, headers=headers)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # missing when still running
                content = response.json()
                if "succeeded" in content["data"]["status"]:
                    insist = False
                else:
                    time.sleep(5)
                    insist = (datetime.utcnow().timestamp() - test_start_time) <= 300

            self.assertIn("succeeded", content["data"]["status"])
            self.assertEqual(1, content["data"]["status"]["succeeded"])
            self.assertEqual(notebook_name, content["data"]["metadata"]["annotations"]["analitico.ai/notebook-name"])

            url = reverse("api:recipe-files", args=(receipe_id, notebook_name))
            response = requests.get(server + url, headers=headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # assert notebook has been run with no exceptions
            notebook = response.json()
            execution_status = notebook["metadata"]["papermill"]
            notebook_start_time = dateutil.parser.parse(execution_status["start_time"]).timestamp()
            notebook_end_time = dateutil.parser.parse(execution_status["end_time"]).timestamp()
            self.assertGreaterEqual(notebook_start_time, test_start_time)
            self.assertGreaterEqual(notebook_end_time, notebook_start_time)
            self.assertEqual(None, execution_status["exception"])

        finally:
            # clean up
            if "job_id" in locals():
                k8_job_delete(job_id)

    @tag("slow", "k8s", "live")
    def test_k8s_jobs_build(self):
        test_start_time = time.time()

        # named: K8Tests.test_k8s_jobs_run
        receipe_id = "rx_x5b1npmn"
        notebook_name = "notebook.ipynb"
        server = "https://staging.analitico.ai"
        headers = {"Authorization": "Bearer tok_demo1_croJ7gVp4cW9", "Content-Type": "application/json"}

        # build the recipe
        url = reverse("api:recipe-k8-jobs", args=(receipe_id, analitico.ACTION_BUILD))
        response = requests.post(server + url, data=json.dumps({"data": {"notebook": notebook_name}}), headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        try:
            content = response.json()
            job_id = content["data"]["metadata"]["name"]
            target_id = content["data"]["metadata"]["labels"]["analitico.ai/target-id"]
            url = reverse("api:recipe-k8-jobs", args=(receipe_id, job_id))

            # wait to complete
            insist = True
            while insist:
                response = requests.get(server + url, headers=headers)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # missing when still running
                content = response.json()
                if "succeeded" in content["data"]["status"]:
                    insist = False
                else:
                    time.sleep(5)
                    insist = (time.time() - test_start_time) <= 900

            self.assertIn("succeeded", content["data"]["status"])
            self.assertEqual(1, content["data"]["status"]["succeeded"])
            self.assertEqual(notebook_name, content["data"]["metadata"]["annotations"]["analitico.ai/notebook-name"])

            # when build completes the target model is updated with the
            # docker image specifications
            url = reverse("api:model-detail", args=(target_id,))
            response = requests.get(server + url, headers=headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()

            # notebook name is saved in the model
            self.assertIn("notebook", content["data"]["attributes"])
            self.assertEqual(notebook_name, content["data"]["attributes"]["notebook"])
            # notebook is copied in the target path on the drive
            file_url = reverse("api:model-files", args=(target_id, notebook_name))
            response = requests.get(server + file_url, headers=headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertIn("docker", content["data"]["attributes"])
            docker = content["data"]["attributes"]["docker"]
            image_describe_cmd = ["gcloud", "container", "images", "describe", "--format", "json", docker["image"]]

            # it raises exception if docker image is not found
            sdout, sderr = subprocess_run(image_describe_cmd)
            self.assertEqual(sderr, "")

            # metadata with metrics are stored in the model
            self.assertIn("metadata", content["data"]["attributes"])
            metadata = content["data"]["attributes"]["metadata"]
            self.assertIn("scores", metadata)
            self.assertIn("number_of_lines", metadata["scores"])

            self.k8s_deploy_and_test(target_id, receipe_id)

        finally:
            # clean up job, model and image
            if job_id:
                k8_job_delete(job_id)
                url = reverse("api:model-detail", args=(target_id,))
                requests.delete(server + url, headers=headers)
                if "docker" in locals() and "image" in docker:
                    subprocess_run(
                        "gcloud container images delete --force-delete-tags --quiet " + docker["image"], shell=True
                    )

    def k8s_deploy_and_test(self, model_id, receipe_id):
        """ This test is called by the test `test_k8s_jobs_build`. """
        server = "https://staging.analitico.ai"
        headers = {"Authorization": "Bearer tok_demo1_croJ7gVp4cW9"}

        # deploy the build model
        url = reverse("api:model-k8-deploy", args=(model_id, K8_STAGE_STAGING))
        response = requests.post(server + url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        k8_service_name = content["data"]["response"]["metadata"]["name"]

        # wait for deploy to complete
        time.sleep(60)

        try:
            # retrieve deployed service info
            url = reverse("api:recipe-k8-ksvc", args=(receipe_id, K8_STAGE_STAGING))
            response = requests.get(server + url, headers=headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()
            service_url = content["data"]["status"]["url"]

            # notebook has been written to install packages and require them
            # when calling for prediction. If the build and the deployed
            # worked, the endpoint responses fine
            response = requests.get(service_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()
            self.assertIn("free_joke", content["data"])
        finally:
            # clean up service
            subprocess_run("kubectl delete kservice -n cloud " + k8_service_name, shell=True)

    @tag("slow", "k8s", "live")
    def test_k8s_jobs_run_and_build(self, notebook_name=None):
        try:
            # required utc timestamp for date comparison
            test_start_time = datetime.utcnow().timestamp()

            # named: K8Tests.test_k8s_jobs_run
            receipe_id = "rx_x5b1npmn"
            # default or custom name
            notebook_name = "notebook.ipynb" if not notebook_name else notebook_name
            server = "https://staging.analitico.ai"
            headers = {"Authorization": "Bearer tok_demo1_croJ7gVp4cW9", "Content-Type": "application/json"}

            # run and build the recipe
            url = reverse("api:recipe-k8-jobs", args=(receipe_id, analitico.ACTION_RUN_AND_BUILD))
            response = requests.post(
                server + url, data=json.dumps({"data": {"notebook": notebook_name}}), headers=headers
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            content = response.json()
            job_id = content["data"]["metadata"]["name"]
            target_id = content["data"]["metadata"]["labels"]["analitico.ai/target-id"]
            url = reverse("api:recipe-k8-jobs", args=(receipe_id, job_id))

            # wait to complete
            insist = True
            while insist:
                response = requests.get(server + url, headers=headers)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # missing when still running
                content = response.json()
                if "succeeded" in content["data"]["status"]:
                    insist = False
                else:
                    time.sleep(5)
                    insist = (datetime.utcnow().timestamp() - test_start_time) <= 900

            self.assertIn("succeeded", content["data"]["status"])
            self.assertEqual(1, content["data"]["status"]["succeeded"])
            self.assertEqual(notebook_name, content["data"]["metadata"]["annotations"]["analitico.ai/notebook-name"])

            url = reverse("api:recipe-files", args=(receipe_id, notebook_name))
            response = requests.get(server + url, headers=headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # assert notebook has been run with no exceptions
            notebook = response.json()
            execution_status = notebook["metadata"]["papermill"]
            notebook_start_time = dateutil.parser.parse(execution_status["start_time"]).timestamp()
            notebook_end_time = dateutil.parser.parse(execution_status["end_time"]).timestamp()
            self.assertGreaterEqual(notebook_start_time, test_start_time)
            self.assertGreaterEqual(notebook_end_time, notebook_start_time)
            self.assertEqual(None, execution_status["exception"])

            # when build completes the target model is updated with the
            # docker image specifications
            url = reverse("api:model-detail", args=(target_id,))
            response = requests.get(server + url, headers=headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            content = response.json()
            self.assertIn("docker", content["data"]["attributes"])

            docker = content["data"]["attributes"]["docker"]
            image_describe_cmd = ["gcloud", "container", "images", "describe", "--format", "json", docker["image"]]
            # it raises exception if docker image is not found
            sdout, sderr = subprocess_run(image_describe_cmd)
            self.assertEqual(sderr, "")

        finally:
            # clean up job, model and image
            if job_id:
                k8_job_delete(job_id)
                url = reverse("api:model-detail", args=(target_id,))
                requests.delete(server + url, headers=headers)
                if "docker" in locals() and "image" in docker:
                    subprocess_run(
                        "gcloud container images delete --force-delete-tags --quiet " + docker["image"], shell=True
                    )

    @tag("slow", "k8s")
    def test_k8s_jobs_run_and_build_custom_notebook_name(self):
        self.test_k8s_jobs_run_and_build("my notebook.ipynb")
        self.test_k8s_jobs_run_and_build("subfolder/another my-notebook.ipynb")
        self.test_k8s_jobs_run_and_build("/subfolder/another my-notebook.ipynb")

    def test_get_job_that_does_not_exist(self):
        """ Expect 404 not found when a job does not exist """
        self.auth_token(self.token1)
        url = reverse("api:notebook-k8-jobs", args=(self.item_id, "jb-imafakejob"))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @tag("k8s")
    def test_job_delete(self):
        # job posted on workspace `ws1`
        job_id, job = self.job_run_notebook()
        url = reverse("api:notebook-k8-jobs", args=(self.item_id, job_id))

        # user without permission cannot retrieve the list
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.auth_token(self.token1)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # wait for the pod's default grace period of 30secs
        time.sleep(5)

        # job is deleted
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # try to delete job again but it's not find
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @tag("k8s")
    def test_k8_wait_for_condition(self):
        # non existent resource
        try:
            k8_wait_for_condition("cloud", "pod/fake", "condition=Ready", timeout=2)
            self.fail("Expected not found exception")
        except AnaliticoException:
            pass

        # ready resource
        service = self.deploy_service(wait=False)
        status, _ = k8_wait_for_condition(
            "cloud", "pod", "condition=Ready", labels="analitico.ai/item-id=" + self.item_id
        )
        self.assertIn("condition met", status)

    ##
    ## Test Jupyter
    ##

    @tag("k8s", "slow")
    def test_k8_jupyter_get(self):
        # user CANNOT retrieve Jupyters from workspaces he does not have access to
        self.auth_token(self.token2)
        url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        try:
            # Jupyter deployed in workspace `ws1`
            deployment = self.deploy_jupyter()
            jupyter_name = get_dict_dot(deployment, "metadata.labels.app")

            # all Jupyters in the workspace
            self.auth_token(self.token1)
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id,))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            items = get_dict_dot(response.json(), "data.items", [])
            self.assertEqual(1, len(items))
            self.assertEqual(get_dict_dot(deployment, "metadata.name"), get_dict_dot(items[0], "metadata.name"))

            # user cannot retrieve a specific Jupyter from workspaces he does not have access to
            self.auth_token(self.token2)
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # get specific jupyter
            self.auth_token(self.token1)
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            response = self.client.get(url)
            actual_jupyter = response.json().get("data")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(get_dict_dot(deployment, "metadata.name"), get_dict_dot(actual_jupyter, "metadata.name"))

            # user cannot retrieve a specific jupyter from another workspace he does not have access to
            self.auth_token(self.token2)
            url = reverse("api:workspace-k8-jupyters", args=(self.ws2.id, jupyter_name))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s", "live")
    def test_deploy_jupyter_default_settings(self):
        try:
            deployment = self.deploy_jupyter()

            # assert the jupyter to be setup properly

            deployment_name = get_dict_dot(deployment, "metadata.name")
            labels = get_dict_dot(deployment, "metadata.labels")
            jupyter_name = labels["app"]
            # eg, jupyter-123abc-deployment
            self.assertIn(labels["app"], deployment_name)
            self.assertEqual(labels["analitico.ai/service"], "jupyter")
            self.assertEqual(labels["analitico.ai/workspace-id"], self.ws1.id)

            annotations = get_dict_dot(deployment, "metadata.annotations")
            jupyter_url = annotations["analitico.ai/jupyter-url"]
            self.assertEqual(jupyter_url, f"https://{jupyter_name}.cloud.analitico.ai")
            self.assertEqual(annotations["analitico.ai/enable-scale-to-zero"], "true")
            self.assertEqual(annotations["analitico.ai/scale-to-zero-grace-period"], "60")

            token = annotations.get("analitico.ai/jupyter-token", "")
            self.assertTrue(token != "")

            container = get_dict_dot(deployment, "spec.template.spec.containers")[0]
            resources = container["resources"]
            self.assertEqual("500m", resources["requests"]["cpu"])
            self.assertEqual(str(size_to_bytes("8Gi")), resources["requests"]["memory"])
            self.assertEqual("0", resources["requests"]["nvidia.com/gpu"])

            self.assertEqual("4", resources["limits"]["cpu"])
            self.assertEqual(str(size_to_bytes("8Gi")), resources["limits"]["memory"])
            self.assertEqual("0", resources["limits"]["nvidia.com/gpu"])

            # Jupyter should be ready when we get the response
            k8_wait_for_condition(
                K8_DEFAULT_NAMESPACE, "pod", "condition=Ready", labels="app=" + jupyter_name, timeout=2
            )

            # access denied without token (redirected to /login)
            response = requests.get(jupyter_url, allow_redirects=True)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("/login", response.url)

            # jupyter runs and logins (redirected to /tree)
            url = f"{jupyter_url}?token={token}"
            response = requests.get(url, allow_redirects=True)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("/tree", response.url)

            # delete jupyter when workspace is removed
            self.ws1.delete()
            k8_wait_for_condition(K8_DEFAULT_NAMESPACE, "pod", "delete", labels="app=" + jupyter_name, timeout=90)

            # check all deployed resources to be deleted
            response, _ = kubectl(
                K8_DEFAULT_NAMESPACE,
                "get",
                "deployment,service,virtualService,pod,secret",
                args=["--selector", f"app={jupyter_name}"],
            )
            # all resources removed
            self.assertEqual(0, len(response["items"]))
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s", "live")
    def test_jupyter_deploy_workspace_settings(self):
        try:
            # provision the workspace with settings that should
            # have come from subscription metadata
            settings = {
                "settings": {
                    "max_instances": 1,
                    "replicas": 1,
                    "enable_scale_to_zero": "false",
                    "scale_to_zero_grace_period": "30",
                    "requests": {"cpu": "100m", "memory": "100M", "nvidia.com/gpu": 0},
                    "limits": {"cpu": "2", "memory": "200Mi", "nvidia.com/gpu": 0},
                }
            }
            self.ws1.set_attribute("jupyter", settings)
            self.ws1.save()

            deployment = self.deploy_jupyter()

            # expect jupyter to be deployed with the workspace
            # settings specified above

            annotations = get_dict_dot(deployment, "metadata.annotations")
            self.assertEqual(annotations["analitico.ai/enable-scale-to-zero"], "false")
            self.assertEqual(annotations["analitico.ai/scale-to-zero-grace-period"], "30")

            container = get_dict_dot(deployment, "spec.template.spec.containers")[0]
            resources = container["resources"]
            self.assertEqual("100m", resources["requests"]["cpu"])
            self.assertEqual("100M", resources["requests"]["memory"])
            self.assertEqual("0", resources["requests"]["nvidia.com/gpu"])

            self.assertEqual("2", resources["limits"]["cpu"])
            self.assertEqual(str(size_to_bytes("200Mi")), resources["limits"]["memory"])
            self.assertEqual("0", resources["limits"]["nvidia.com/gpu"])
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s", "live")
    def test_jupyter_deploy_custom_settings(self):
        try:
            # custom settings are limited by those specified in the workspace
            settings = {
                "settings": {
                    "enable_scale_to_zero": "false",
                    "scale_to_zero_grace_period": "120",
                    "limits": {"cpu": "1", "memory": "32Gi", "nvidia.com/gpu": 1},
                }
            }
            deployment = self.deploy_jupyter(custom_settings=settings)

            # expect jupyter to be deployed with the settings
            # specified above except for the memory and the GPU

            annotations = get_dict_dot(deployment, "metadata.annotations")
            self.assertEqual(annotations["analitico.ai/enable-scale-to-zero"], "false")
            self.assertEqual(annotations["analitico.ai/scale-to-zero-grace-period"], "60")

            container = get_dict_dot(deployment, "spec.template.spec.containers")[0]
            resources = container["resources"]
            self.assertEqual("500m", resources["requests"]["cpu"])
            self.assertEqual(str(size_to_bytes("8Gi")), resources["requests"]["memory"])
            self.assertEqual("0", resources["requests"]["nvidia.com/gpu"])

            self.assertEqual("1", resources["limits"]["cpu"])
            self.assertEqual(str(size_to_bytes("8Gi")), resources["limits"]["memory"])
            self.assertEqual("0", resources["limits"]["nvidia.com/gpu"])
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s", "live")
    def test_jupyter_deploy_max_instances_reached(self):
        try:
            # deploy the first jupyter
            self.deploy_jupyter()

            settings = {
                "settings": {
                    ## workspace is limited to 1 jupyter instance only ##
                    "max_instances": 1,
                    "enable_scale_to_zero": "false",
                    "scale_to_zero_grace_period": "30",
                    "requests": {"cpu": "100m", "memory": "100M", "nvidia.com/gpu": 0},
                    "limits": {"cpu": "2", "memory": "200Mi", "nvidia.com/gpu": 0},
                }
            }
            self.ws1.set_attribute("jupyter", settings)
            self.ws1.save()

            url = reverse("api:workspace-k8-jupyter-deploy", args=(self.ws1.id,))
            self.auth_token(self.token1)
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
            self.assertEqual(
                response.json().get("error").get("title"),
                "The maximum number of Jupyter instances has been reached (max 1 / current 1)",
            )
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s", "live")
    def test_jupyter_update_deployment(self):
        try:
            # deploy update fails when the given jupyter does not exist
            jupyter_name = "fake-jupyter"
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            self.auth_token(self.token1)
            response = self.client.put(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # deploy a jupyter for the workspace `ws1`
            deployment = self.deploy_jupyter()
            jupyter_name = get_dict_dot(deployment, "metadata.labels.app")

            # user cannot update jupyter that he doesn't have access to
            self.auth_token(self.token2)
            url = reverse("api:workspace-k8-jupyters", args=(self.ws2.id, jupyter_name))
            response = self.client.put(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # user cannot update jupyter from a workspace he doesn't have access to
            self.auth_token(self.token2)
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            response = self.client.put(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # user can update his jupyter deployment specs while kicking it off.
            # scale to zero to test kickoff on jupyter update
            response, _ = kubectl(
                K8_DEFAULT_NAMESPACE,
                "scale",
                "statefulSet/" + get_dict_dot(deployment, "metadata.name"),
                args=["--replicas=0"],
            )
            k8_wait_for_condition(K8_DEFAULT_NAMESPACE, "pod", "delete", labels="app=" + jupyter_name)

            # update jupyter with these settings
            custom_settings = {
                "settings": {
                    "scale_to_zero_grace_period": "20",
                    "limits": {"cpu": "1", "memory": "8Gi", "nvidia.com/gpu": 0},
                }
            }
            self.auth_token(self.token1)
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            response = self.client.put(url, data=custom_settings)
            self.assertStatusCode(response)

            deployment = response.json().get("data", {})

            # jupyter instance has been kicked off (scaled up)
            self.assertEqual(1, get_dict_dot(deployment, "spec.replicas"))

            # jupyter configuration has been updated
            annotations = get_dict_dot(deployment, "metadata.annotations")
            self.assertEqual(annotations["analitico.ai/enable-scale-to-zero"], "true")
            self.assertEqual(annotations["analitico.ai/scale-to-zero-grace-period"], "20")

            container = get_dict_dot(deployment, "spec.template.spec.containers")[0]
            resources = container["resources"]
            self.assertEqual("1", resources["limits"]["cpu"])
            self.assertEqual(str(size_to_bytes("8Gi")), resources["limits"]["memory"])
            self.assertEqual("0", resources["limits"]["nvidia.com/gpu"])
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s", "live")
    def test_jupyter_stop_manually(self):
        """ Stop Jupyter pod manually with an explicit request """
        try:
            jupyter = self.deploy_jupyter()
            jupyter_name = get_dict_dot(jupyter, "metadata.labels.app")

            # stop Jupyter by setting replicas to zero
            settings = {"settings": {"replicas": 0}}
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            response = self.client.put(url, data=settings, format="json")
            self.assertApiResponse(response)
            jupyter = response.json().get("data")

            self.assertEqual(0, get_dict_dot(jupyter, "spec.replicas"))
            k8_wait_for_condition(K8_DEFAULT_NAMESPACE, "pod", "delete", labels="app=" + jupyter_name)
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s", "live")
    def test_jupyter_kickoff_and_contact_jupyter(self):
        """ 
        Deploy a Jupyter with zero replicas then kick it off
        and expect it to be up and running
        """
        try:
            jupyter = self.deploy_jupyter()
            jupyter_name = get_dict_dot(jupyter, "metadata.labels.app")

            # scale to zero to test kickoff
            response, _ = kubectl(
                K8_DEFAULT_NAMESPACE,
                "scale",
                "statefulSet/" + get_dict_dot(jupyter, "metadata.name"),
                args=["--replicas=0"],
            )
            k8_wait_for_condition(K8_DEFAULT_NAMESPACE, "pod", "delete", labels="app=" + jupyter_name)

            self.auth_token(self.token1)
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            response = self.client.put(url)
            self.assertStatusCode(response)

            jupyter = response.json().get("data", {})

            # Jupyter instance has been kicked off (scaled up)
            self.assertEqual(1, get_dict_dot(jupyter, "spec.replicas"))

            # Jupyter is up and running
            annotations = get_dict_dot(jupyter, "metadata.annotations")
            jupyter_url = annotations["analitico.ai/jupyter-url"]
            response = requests.get(jupyter_url, allow_redirects=True)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s", "live")
    def test_jupyter_autoscaler_cron_is_up_and_running(self):
        """ 
        Test the scale to zero functionality. 
        This test is a live test, it deploys a Jupyter and waits for it
        to be scaled to zero. 
        It means that the test requires an up-and-running cron that checks
        and performs scale to zero on enabled services. 
        """
        try:
            # deploy Jupyter with 1 min grace period
            settings = {
                "settings": {"max-instances": 1, "enable-scale-to-zero": "true", "scale-to-zero-grace-period": "1"}
            }
            jupyter = self.deploy_jupyter(custom_settings=settings)

            jupyter_name = get_dict_dot(jupyter, "metadata.name")
            namespace = get_dict_dot(jupyter, "metadata.namespace")
            url = get_dict_dot(jupyter, "metadata.annotations").get("analitico.ai/jupyter-url")
            app = get_dict_dot(jupyter, "metadata.labels.app")

            # call Jupyter to generate http and cpu metric
            # and wait for the autoscaler to bring it to zero
            response = requests.get(url)
            self.assertApiResponse(response)
            # it should take around 1/2 minutes, timeout to 5 minutes for mercy
            k8_wait_for_condition(
                namespace, "pod", "delete", labels=f"app={app},analitico.ai/workspace-id={self.ws1.id}", timeout=300
            )

            # confirm replicas set to 0
            jupyter, _ = kubectl(namespace, "get", "statefulset/" + jupyter_name)
            self.assertEqual(0, get_dict_dot(jupyter, "spec.replicas"))
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("slow", "k8s")
    def test_k8_scale_to_zero(self):
        """ Deploy a Jupyter with scale to zero enabled and check synchronous for it to be actually scaled. """
        try:
            # deploy Jupyter with 1 min grace period
            settings = {
                "settings": {"max_instances": 1, "enable_scale_to_zero": "true", "scale_to_zero_grace_period": "1"}
            }
            jupyter = self.deploy_jupyter(custom_settings=settings)

            name = get_dict_dot(jupyter, "metadata.name")
            namespace = get_dict_dot(jupyter, "metadata.namespace")
            url = get_dict_dot(jupyter, "metadata.annotations").get("analitico.ai/jupyter-url")
            app = get_dict_dot(jupyter, "metadata.labels.app")

            # call Jupyter to generate http and cpu metric
            # and wait for the autoscaler to bring it to zero
            response = requests.get(url)
            self.assertApiResponse(response)

            # run autoscaler
            retry = True
            start = time.time()
            attempts = 0
            while retry:
                attempts = attempts + 1
                scaled, unable = k8_scale_to_zero([jupyter])
                # it should take around 1/2 minutes, timeout to 5 minutes for mercy
                retry = scaled == 0 and unable == 0 and time.time() - start < 300
                if retry:
                    time.sleep(40)

            # at least two attempts if it's respected the grace period of 1 minute
            self.assertGreaterEqual(attempts, 2, "scale to zero is not respecting the grace period")

            # confirm replicas set to 0
            self.assertEqual(1, scaled)
            jupyter, _ = kubectl(namespace, "get", "statefulset/" + name)
            self.assertEqual(0, get_dict_dot(jupyter, "spec.replicas"))
        finally:
            k8_jupyter_deallocate(self.ws1)

    @tag("k8s")
    def test_k8_jupyter_delete(self):
        try:
            # Jupyter deployed in workspace `ws1`
            jupyter = self.deploy_jupyter()

            namespace = get_dict_dot(jupyter, "metadata.namespace")
            jupyter_name = get_dict_dot(jupyter, "metadata.labels.app")

            # user cannot delete a Jupyter from a workspace he doesn't have access to
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            self.auth_token(self.token2)
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # user cannot delete a Jupyter he doesn't have access to
            url = reverse("api:workspace-k8-jupyters", args=(self.ws2.id, jupyter_name))
            self.auth_token(self.token2)
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # delete specific jupyter
            url = reverse("api:workspace-k8-jupyters", args=(self.ws1.id, jupyter_name))
            self.auth_token(self.token1)
            response = self.client.delete(url)
            self.assertApiResponse(response, status_code=status.HTTP_204_NO_CONTENT)
        finally:
            k8_jupyter_deallocate(self.ws1)
