import os
import os.path
import json
import time

from django.urls import reverse
from rest_framework import status

# conflicts with django's dynamically generated model.objects

# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

from analitico.constants import ACTION_PROCESS, ACTION_DEPLOY
from analitico.utilities import read_json

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
    def OFFtest_k8_build_and_deploy_docker(self):
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

        service = api.k8.k8_deploy(notebook, endpoint)
        self.assertEquals(service["type"], "analitico/service")
        self.assertEquals(service["name"], self.endpoint_id_normalized)
        self.assertEquals(service["namespace"], "cloud")
        self.assertIn("url", service)

        # give it a moment so it can, maybe, deploy...
        time.sleep(10)

        # retrieve service information from kubernetes cluster
        service = api.k8.k8_get_item_service(endpoint)
        self.assertEquals(service["apiVersion"], "serving.knative.dev/v1alpha1")
        self.assertEquals(service["kind"], "Service")
        self.assertIn("metadata", service)
        self.assertIn("spec", service)
        self.assertIn("status", service)

    ##
    ## K8s APIs
    ##

    # TODO we need to setup the credentials for kubectl in gitlab CI/CD
    def OFFtest_k8s_get_nodes(self):
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
