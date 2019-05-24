import os
import os.path
import json

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
from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import AnaliticoApiTestCase

import logging

logger = logging.getLogger("analitico")


class EndpointsTests(AnaliticoApiTestCase):
    """ Test notebooks operations via APIs """

    # TODO move these tests to live testing
    def OFFtest_ep_deploy_notebook(self):
        # Builds a notebook into a docker, then deploys docker to the cloud
        # we're using an id with UPPERCASE chars to test for a cloud run requirement
        # of lowercase only IDs
        endpoint_id = "ep_TEST_001"
        target_id = "nb_TEST_001"  # help registry cleanups

        endpoint_id_normalized = "ep-test-001"
        target_id_normalized = "nb-test-001"

        # create an endpoin  notebook that will be compiled to docker
        self.post_notebook("notebook11.ipynb", target_id)

        # create an endpoint that we will be deploying this notebook too
        endpoint = Endpoint(id=endpoint_id, workspace=self.ws1)
        endpoint.save()

        # run a job to deploy the notebook to the endpoint. the action is run on the endpoint.
        # the targer of the deploy action is the notebook that needs to be dockerized and deployed
        url = reverse("api:endpoint-job-action", args=(endpoint_id, ACTION_DEPLOY)) + "?async=false"
        response = self.client.post(url, data={"target_id": target_id}, format="json")
        self.assertApiResponse(response)

        # check job, targets, status, etc
        # logging.info(f"response.content: {str(response.content)}")
        job = response.data
        self.assertEqual(job["attributes"]["action"], "endpoint/deploy")
        self.assertEqual(job["attributes"]["status"], "completed")
        self.assertEqual(job["attributes"]["item_id"], endpoint_id)
        self.assertEqual(job["attributes"]["target_id"], target_id)

        # docker that was built for deployment
        docker = job["attributes"]["docker"]
        self.assertEquals(docker["type"], "analitico/docker")
        self.assertEquals(docker["image_name"], f"eu.gcr.io/analitico-api/{target_id_normalized}")  # normalized
        self.assertIn(f"gcr.io/analitico-api/{target_id_normalized}@sha256:", docker["image"])
        self.assertIn("sha256:", docker["image_id"])

        service = job["attributes"]["service"]
        self.assertEquals(service["type"], "analitico/service")
        self.assertEquals(service["name"], endpoint_id_normalized)
        self.assertEquals(service["namespace"], "cloud")
        self.assertIn("url", service)

        # retrieve realtime service status for the service running on the endpoint
        url = reverse("api:endpoint-service", args=(endpoint_id,))
        response = self.client.get(url, data={"target_id": target_id}, format="json")
        self.assertApiResponse(response)
        service = response.data
        self.assertEquals(service["apiVersion"], "serving.knative.dev/v1alpha1")
        self.assertEquals(service["kind"], "Service")
        self.assertIn("metadata", service)
        self.assertIn("spec", service)
        self.assertIn("status", service)
