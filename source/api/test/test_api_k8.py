import os
import os.path
import json
import time

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
        time.sleep(10)
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

        # request fails time range
        self.auth_token(self.token1)
        response = self.client.get(url, data={"metric": "flask_http_request_total", "time_range": "this-is-not-a-time-range"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # admin user CAN get metrics
        self.auth_token(self.token1)
        response = self.client.get(url, data={"metric": "flask_http_request_total"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # expect requested metric from specific service
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["data"]["result"]), 1) # one per revision (if any)
        for metric in data["data"]["result"]:
            self.assertEqual(metric["metric"]["serving_knative_dev_service"], self.endpoint_id_normalized)

        # filter a specific metric over a specific time range
        response = self.client.get(url, data={"metric": "flask_http_request_total", "time_range": "30m"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(data["status"], "success")
        for metric in data["data"]["result"]:
            self.assertEqual(metric["metric"]["serving_knative_dev_service"], self.endpoint_id_normalized)
            self.assertEqual(metric["metric"]["__name__"], "flask_http_request_total")

    @tag("slow", "docker", "k8s")
    def test_k8s_get_logs(self):
        self.deploy_service()
        url = reverse("api:k8-logs", args=(self.endpoint_id,))

        # user CANNOT read logs from items he does not have access to
        self.auth_token(self.token3)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # admin user CAN get metrics
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertGreater(len(data["hits"]["hits"]), 20)
        self.assertEqual(data["timed_out"], False)
        self.assertGreater(data["hits"]["total"], 20)

        # limit the number of results with ?size= parameter
        response = self.client.get(url, data={"size": 20}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(len(data["hits"]["hits"]), 20)
        self.assertEqual(data["timed_out"], False)
        self.assertGreater(data["hits"]["total"], 50)

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
        self.assertGreater(len(data["hits"]["hits"]), 20)
        for d in data["hits"]["hits"]:
            self.assertEqual("info", d["_source"]["level"])
