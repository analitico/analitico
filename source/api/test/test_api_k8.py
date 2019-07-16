import os
import os.path
import json
import time
import requests

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
import api.k8

from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import AnaliticoApiTestCase

import logging

logger = logging.getLogger("analitico")


class K8Tests(AnaliticoApiTestCase):
    """ Test kubernets API to build and deploy on knative """

    endpoint_id = "ep_TEST_001"
    target_id = "nb_TEST_001"  # help registry cleanups
    endpoint_id_normalized = "ep-test-001"
    target_id_normalized = "nb-test-001"

    # TODO cannot run this in CI/CD pipeline, should be added to live testing?
    @tag("slow", "docker", "k8s")
    def test_k8_build_and_deploy_docker(self):
        """ Test building a docker from a notebook then deploying it """

        self.post_notebook("notebook11.ipynb", self.target_id)
        notebook = Notebook.objects.get(pk=self.target_id)
        endpoint = Endpoint(id=self.endpoint_id, workspace=self.ws1)
        endpoint.save()

        docker = api.k8.k8_build(notebook)
        self.assertEquals(docker["type"], "analitico/docker")
        self.assertEquals(docker["image_name"], f"eu.gcr.io/analitico-api/{self.target_id_normalized}")  # normalized
        self.assertIn(f"gcr.io/analitico-api/{self.target_id_normalized}@sha256:", docker["image"])
        self.assertIn("sha256:", docker["image_id"])

        logger.info("Run this image locally with:")
        logger.info(f"docker run -e PORT=8080 -p 8080:8080 {docker['image']}")

        service = api.k8.k8_deploy(notebook, endpoint)
        self.assertEquals(service["type"], "analitico/service")
        self.assertEquals(service["name"], self.endpoint_id_normalized)
        self.assertEquals(service["namespace"], "cloud")
        self.assertIn("url", service)

        # give it a moment so it can, maybe, deploy...
        time.sleep(10)

        # retrieve service information from kubernetes cluster
        service, _ = subprocess_run(
            cmd_args=[
                "kubectl",
                "get",
                "ksvc",
                self.endpoint_id_normalized,
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

    def deploy_service(self):
        self.post_notebook("notebook11.ipynb", self.target_id)
        notebook = Notebook.objects.get(pk=self.target_id)
        endpoint = Endpoint(id=self.endpoint_id, workspace=self.ws1)
        endpoint.save()

        docker = api.k8.k8_build(notebook)
        service = api.k8.k8_deploy(notebook, endpoint)
        time.sleep(15)
        return service

    @tag("slow", "docker", "k8s")
    def test_k8s_get_metrics(self):
        self.deploy_service()
        url = reverse("api:k8-metrics", args=(self.endpoint_id,))

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

        # admin user CAN get metrics
        self.auth_token(self.token1)
        response = self.client.get(url, data={"metric": "container_cpu_load"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # expect requested metric from specific service
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["data"]["result"]), 1)  # one per revision (if any)
        for metric in data["data"]["result"]:
            self.assertIn(self.endpoint_id_normalized, metric["metric"]["pod_name"])

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
            self.assertIn(self.endpoint_id_normalized, metric["metric"]["pod_name"])

    @tag("slow", "docker", "k8s", "live")
    def test_k8s_get_logs(self):
        self.deploy_service()
        url = reverse("api:k8-logs", args=(self.endpoint_id,))

        # /echo endpoint will generate a log message at the given level
        endpoint_echo = f"https://{self.endpoint_id_normalized}.cloud.analitico.ai/echo"

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

        # limit the number of results with ?size= parameter
        response = self.client.get(url, data={"size": 10}, format="json")
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

    def test_k8s_jobs_run(self):
        # k8s / write unit tests for k8_jobs_create #296
        # k8_jobs_create...
        pass

    def test_k8s_jobs_build(self):
        # k8s / write unit tests for k8_jobs_create #296
        # k8_jobs_create...
        pass

    def test_k8s_jobs_run_and_build(self):
        # k8s / write unit tests for k8_jobs_create #296
        # k8_jobs_create...
        pass
