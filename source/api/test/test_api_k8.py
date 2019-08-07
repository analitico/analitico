import os
import os.path
import json
import time
import requests
import dateutil.parser

from django.test import tag
from django.urls import reverse
from rest_framework import status

# conflicts with django's dynamically generated model.objects

# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

from analitico.constants import ACTION_PROCESS, ACTION_DEPLOY
from analitico.utilities import read_json, subprocess_run

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

    def deploy_service(self):
        self.auth_token(self.token1)
        self.post_notebook("notebook11.ipynb", self.item_id)
        notebook = Notebook.objects.get(pk=self.item_id)
        # pre run and built image tagged with `K8Tests_test_k8_deploy`
        notebook.set_attribute(
            "docker",
            {
                "type": "analitico/docker",
                "image": "eu.gcr.io/analitico-api/rx-fvdmbmon@sha256:bd5feff21345f0a9d3ae855a925442487936d85968b823fddb92d10c287892e3",
                "image_name": "eu.gcr.io/analitico-api/rx-fvdmbmon:K8Tests_test_k8_deploy",
                "image_id": "sha256:bd5feff21345f0a9d3ae855a925442487936d85968b823fddb92d10c287892e3",
            },
        )
        notebook.save()

        service = k8_deploy_v2(notebook, notebook, self.stage)
        self.assertEquals(service["type"], "analitico/service")
        self.assertEquals(service["name"], self.item_id_normalized)
        self.assertEquals(service["namespace"], "cloud")
        self.assertIn("url", service)

        time.sleep(15)
        return service

    def delete_job(self, job_id: str):
        subprocess_run(cmd_args=["kubectl", "delete", "job", job_id, "-n", "cloud"])

    def deploy_jupyter(self):
        url = reverse("api:workspace-jupyter", args=(self.ws2.id,))

        self.auth_token(self.token2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.ws2.refresh_from_db()
        return self.ws2

    def job_run_notebook(self, item_id=None):
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

        return job_id

    # TODO cannot run this in CI/CD pipeline, should be added to live testing?
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

    @tag("slow", "k8s", "live")
    def test_k8s_job_logs(self):
        try:
            # run a job to generate logs
            job_id = self.job_run_notebook()
            # wait for logs to be collected
            time.sleep(30)

            url = reverse("api:notebook-k8-job-logs", args=(self.item_id, job_id))

            # user CANNOT read logs from items he does not have access to
            self.auth_token(self.token3)
            response = self.client.get(url, format="json")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # user CANNOT read logs from jobs that does not belong to the item
            self.auth_token(self.token1)
            another_job_id = self.job_run_notebook("nb_anothernotebook")
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
            self.delete_job(job_id)
            self.delete_job(another_job_id)

    @tag("slow", "k8s", "live")
    def test_k8s_jobs_run(self):
        try:
            # required utc timestamp for date comparison
            test_start_time = datetime.datetime.utcnow().timestamp()

            # named: K8Tests.test_k8s_jobs_run
            receipe_id = "rx_x5b1npmn"
            server = "https://staging.analitico.ai"
            headers = {"Authorization": "Bearer tok_demo1_croJ7gVp4cW9"}

            # run the recipe
            url = reverse("api:recipe-k8-jobs", args=(receipe_id, analitico.ACTION_RUN))
            response = requests.post(server + url, headers=headers)
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
                    insist = (datetime.datetime.utcnow().timestamp() - test_start_time) <= 300

            self.assertIn("succeeded", content["data"]["status"])
            self.assertEqual(1, content["data"]["status"]["succeeded"])

            url = reverse("api:recipe-files", args=(receipe_id, "notebook.ipynb"))
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
                self.delete_job(job_id)

    @tag("slow", "k8s", "live")
    def test_k8s_jobs_run_custom_notebook_name(self):
        try:
            test_start_time = time.time()

            # named: K8Tests.test_k8s_jobs_run
            receipe_id = "rx_x5b1npmn"
            # custom notebook
            notebook_name = "my-notebook.ipynb"
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
                    insist = (time.time() - test_start_time) <= 300

            self.assertIn("succeeded", content["data"]["status"])
            self.assertEqual(1, content["data"]["status"]["succeeded"])
            self.assertEqual(notebook_name, content["data"]["metadata"]["labels"]["analitico.ai/notebook-name"])

        finally:
            # clean up
            if "job_id" in locals():
                self.delete_job(job_id)

    @tag("slow", "k8s", "live")
    def test_k8s_jobs_build(self):
        test_start_time = time.time()

        # named: K8Tests.test_k8s_jobs_run
        receipe_id = "rx_x5b1npmn"
        # custom notebook
        notebook_name = "my-notebook.ipynb"
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
                    insist = (time.time() - test_start_time) <= 600                    

            self.assertIn("succeeded", content["data"]["status"])
            self.assertEqual(1, content["data"]["status"]["succeeded"])
            self.assertEqual(notebook_name, content["data"]["metadata"]["labels"]["analitico.ai/notebook-name"])

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

            # TODO sdk / set_metric save in metadata.json #350 
            # metadata with metrics are stored in the model
            # self.assertIn("metadata", content["data"]["attributes"])
            # metadata = content["data"]["attributes"]["metadata"]
            # self.assertIn("scores", metadata)
            # self.assertIn("number_of_lines", metadata["scores"])

            self.k8s_deploy_and_test(target_id, receipe_id)

        finally:
            # clean up job, model and image
            if job_id:
                self.delete_job(job_id)
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
        time.sleep(20)

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
    def test_k8s_jobs_run_and_build(self):
        try:
            # required utc timestamp for date comparison
            test_start_time = datetime.datetime.utcnow().timestamp()

            # named: K8Tests.test_k8s_jobs_run
            receipe_id = "rx_x5b1npmn"
            # custom notebook
            notebook_name = "my-notebook.ipynb"
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
                    insist = (datetime.datetime.utcnow().timestamp() - test_start_time) <= 600

            self.assertIn("succeeded", content["data"]["status"])
            self.assertEqual(1, content["data"]["status"]["succeeded"])
            self.assertEqual(notebook_name, content["data"]["metadata"]["labels"]["analitico.ai/notebook-name"])

            url = reverse("api:recipe-files", args=(receipe_id, "notebook.ipynb"))
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
                self.delete_job(job_id)
                url = reverse("api:model-detail", args=(target_id,))
                requests.delete(server + url, headers=headers)
                if "docker" in locals() and "image" in docker:
                    subprocess_run(
                        "gcloud container images delete --force-delete-tags --quiet " + docker["image"], shell=True
                    )

    def test_get_job_that_does_not_exist(self):
        """ Expect 404 not found when a job does not exist """
        job_id = self.job_run_notebook()
        url = reverse("api:notebook-k8-jobs", args={self.item_id, "jb-imafakejob"})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # clean up
        self.delete_job(job_id)

    @tag("slow", "k8s", "live")
    def test_deploy_jupyter(self):
        try:
            # deploy jupyter
            ws2 = self.deploy_jupyter()

            # wait for status to be running
            insist = True
            start_time = time.time()
            while insist:
                # ask to deploy jupyter to update the status of the deployment
                ws2 = self.deploy_jupyter()

                jupyter = ws2.get_attribute("jupyter", [])
                phase = jupyter["servers"][0]["status"]["phase"]
                if phase == "Running":
                    insist = False
                else:
                    time.sleep(5)
                    insist = (time.time() - start_time) <= 300

            # attribute with jupyter deployment details
            self.assertIn("jupyter", ws2.attributes)
            jupyter = ws2.get_attribute("jupyter")

            self.assertIn("servers", jupyter)
            servers = jupyter["servers"]

            self.assertGreaterEqual(1, len(servers))
            jupyter_service_name = servers[0]["name"]
            jupyter_service_namespace = servers[0]["namespace"]
            jupyter_url = servers[0]["url"]
            jupyter_token = servers[0]["token"]

            # access denied without token (redirected to /login)
            response = requests.get(jupyter_url, allow_redirects=True)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("/login", response.url)

            # jupyter runs and logins (redirected to /tree)
            url = f"{jupyter_url}?token={jupyter_token}"
            response = requests.get(url, allow_redirects=True)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("/tree", response.url)

            # delete jupyter when workspace is removed
            ws2.delete()
            # wait for pod termination
            time.sleep(60)
            # check all deployed resources to be deleted
            response = subprocess_run(
                [
                    "kubectl",
                    "get",
                    "deployment,service,virtualService,pod,secret",
                    "-l",
                    f"app={jupyter_service_name}",
                    "-n",
                    jupyter_service_namespace,
                    "-ojson",
                ]
            )
            # all resources removed
            self.assertEqual(0, len(response[0]["items"]))
        except Exception as ex:
            if ws2:
                ws2.refresh_from_db()
                k8_deallocate_jupyter(ws2)
            raise ex

    @tag("slow", "k8s", "live")
    def test_jupyter_is_not_deployed_twice(self):
        try:
            ws2 = self.deploy_jupyter()
            jupyter = ws2.get_attribute("jupyter")
            token = jupyter["servers"][0]["token"]

            time.sleep(10)

            # deploy another jupyter on the same workspace
            ws2 = self.deploy_jupyter()
            jupyter = ws2.get_attribute("jupyter")
            token_redeployed = jupyter["servers"][0]["token"]

            self.assertEqual(token, token_redeployed)
        finally:
            # cleanup
            if ws2:
                ws2.refresh_from_db()
                k8_deallocate_jupyter(ws2)
