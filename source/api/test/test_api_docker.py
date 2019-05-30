import os
import os.path
import json
import time
import docker
import requests
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

from analitico import logger
from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import AnaliticoApiTestCase

import logging

logger = logging.getLogger("analitico")

# port that we use for the HTTP server in our
DOCKER_PORT = 8001


class DockerTests(AnaliticoApiTestCase):
    """ Test building dockers from notebooks for knative deployment """

    notebook_id = "nb_test_delete"  # help registry cleanups
    endpoint_id = "ep_test_delete"

    notebook_id_normalized = "nb-test-delete"
    endpoint_id_normalized = "ep-test-delete"

    # Docker SDK for Python
    # https://docker-py.readthedocs.io/en/stable/index.html

    class DockerNotebookRunner:
        """ A class used to build a docker from a notebook, run it and post HTTP requests to it. """

        def __init__(self, tests, notebook_filename, notebook_id=None, endpoint_id=None):
            self.tests = tests
            self.notebook_filename = notebook_filename
            self.notebook_id = notebook_id if notebook_id else tests.notebook_id
            self.endpoint_id = endpoint_id if endpoint_id else tests.endpoint_id

        def build_docker(self):
            self.tests.post_notebook(self.notebook_filename, self.notebook_id)
            self.notebook = Notebook.objects.get(pk=self.notebook_id)

            self.docker_client = docker.from_env()
            self.docker_build = api.k8.k8_build(self.notebook, push=False)

            self.notebook = Notebook.objects.get(pk=self.notebook_id)
            self.endpoint = Endpoint(id=self.endpoint_id, workspace=self.tests.ws1)
            self.endpoint.save()

        def get_container_url(self, relative_url):
            return f"http://127.0.0.1:{DOCKER_PORT}{relative_url}"

        def get_container_response(self, relative_url, post=None):
            url = self.get_container_url(relative_url)
            return requests.post(url, json=post) if post else requests.get(url)

        def get_container_response_json(self, relative_url, post=None, status_code=200):
            response = self.get_container_response(relative_url, post)
            self.tests.assertEqual(response.status_code, status_code)
            # we don't use response.json() because we want to retain item's order
            response_json = json.loads(response.text, object_pairs_hook=OrderedDict)
            return response, response_json

        def __enter__(self):
            self.build_docker()

            for container in self.docker_client.containers.list():
                if f"{DOCKER_PORT}/tcp" in container.ports:
                    logger.info(f"docker container kill {container}")
                    container.kill()

            self.docker_container = self.docker_client.containers.run(
                self.docker_build["image"],
                detach=True,
                ports={f"{DOCKER_PORT}/tcp": DOCKER_PORT},
                environment={"PORT": DOCKER_PORT},
            )
            # wait for gunicorn to start up
            time.sleep(2)
            return self

        def __exit__(self, *args):
            if self.docker_container:
                self.docker_container.kill()
                self.docker_container = None

    @tag("slow", "docker")
    def test_docker_hello_world(self):
        """ Notebook that returns a string """
        with self.DockerNotebookRunner(self, "notebook-docker-hello-world.ipynb") as runner:
            # test docker build attributes
            image = f"eu.gcr.io/analitico-api/{self.notebook_id_normalized}:latest"
            image_name = f"eu.gcr.io/analitico-api/{self.notebook_id_normalized}"
            self.assertEquals(runner.docker_build["type"], "analitico/docker")
            self.assertEquals(runner.docker_build["image_name"], image_name)  # normalized
            self.assertEquals(runner.docker_build["image"], image)

            response, json = runner.get_container_response_json("/")
            self.assertEqual(json["data"], "Hello Analitico")

    @tag("slow", "docker")
    def test_docker_hello_world_custom_json(self):
        """ Notebook that returns a custom json payload """
        with self.DockerNotebookRunner(self, "notebook-docker-hello-world-custom-json.ipynb") as runner:
            response, json = runner.get_container_response_json("/")
            self.assertEqual(json["custom"], "Hello custom json")

    @tag("slow", "docker")
    def test_docker_hello_world_custom_json_and_status(self):
        """ Notebook that returns a custom json payload, status code, utf-8 encoding """
        with self.DockerNotebookRunner(self, "notebook-docker-hello-world-custom-json-and-status.ipynb") as runner:
            response, json = runner.get_container_response_json("/", status_code=201)

            # response string needs to be UTF-8 encoded for Birgün
            self.assertEqual(json["custom"], "Hello Birgün")

    @tag("slow", "docker")
    def test_docker_handle_no_kwargs(self):
        """ Notebook that returns a string, simpler signature of handle method """
        with self.DockerNotebookRunner(self, "notebook-docker-handle-no-kwargs.ipynb") as runner:
            response, json = runner.get_container_response_json("/")
            self.assertEqual(json["data"], "Hello Analitico, no kwargs")

    @tag("slow", "docker")
    def test_docker_no_handle_method(self):
        """ Notebook that does not declare a handle(event, context) method """
        with self.DockerNotebookRunner(self, "notebook-docker-no-handle-method.ipynb") as runner:
            response, json = runner.get_container_response_json("/", status_code=405)

            self.assertEqual(response.status_code, 405)
            self.assertIn("error", json)
            self.assertIn("meta", json["error"])
            self.assertIn("context", json["error"]["meta"])
            self.assertIn("formatted", json["error"]["meta"])
            self.assertIn("traceback", json["error"]["meta"])

            self.assertIn("The notebook should declare", json["error"]["title"])
            self.assertEqual(json["error"]["code"], "error")
            self.assertEqual(json["error"]["status"], "405")

    @tag("slow", "docker")
    def test_docker_throw_exception(self):
        """ Notebook that throws an Exception """
        with self.DockerNotebookRunner(self, "notebook-docker-throw-exception.ipynb") as runner:
            response, json = runner.get_container_response_json("/", status_code=500)

            self.assertEqual(response.status_code, 500)
            self.assertIn("error", json)
            self.assertIn("meta", json["error"])
            self.assertIn("formatted", json["error"]["meta"])
            self.assertIn("traceback", json["error"]["meta"])

            self.assertEqual("Throwing a regular exception", json["error"]["title"])
            self.assertEqual(json["error"]["code"], "exception")
            self.assertEqual(json["error"]["status"], "500")

    @tag("slow", "docker")
    def test_docker_throw_analitico_exception(self):
        """ Notebook that throws an AnaliticoException """
        with self.DockerNotebookRunner(self, "notebook-docker-throw-analitico-exception.ipynb") as runner:
            response, json = runner.get_container_response_json("/", status_code=402)

            self.assertEqual(response.status_code, 402)
            self.assertIn("error", json)
            self.assertIn("meta", json["error"])
            self.assertIn("formatted", json["error"]["meta"])
            self.assertIn("traceback", json["error"]["meta"])

            self.assertEqual("Throwing a 402 for fun", json["error"]["title"])
            self.assertEqual(json["error"]["code"], "error")
            self.assertEqual(json["error"]["status"], "402")

    @tag("slow", "docker")
    def test_docker_echo_dictionary(self):
        """ Notebook that returns what it was posted """
        with self.DockerNotebookRunner(self, "notebook-docker-echo-dictionary.ipynb") as runner:

            # do a get an pass nothing to it
            response, json = runner.get_container_response_json("/")
            data = json["data"]
            self.assertEqual(data["call"], 1)

            # do a post with a simple dictionary that will be passed as the "event"
            response, json = runner.get_container_response_json("/", post={"key1": "value1"})
            data = json["data"]
            self.assertEqual(data["call"], 2)
            self.assertEqual(data["key1"], "value1")

            # do another POST with different data
            response, json = runner.get_container_response_json("/", post={"key2": "value2"})
            data = json["data"]
            self.assertEqual(data["call"], 3)
            self.assertEqual(data["key2"], "value2")

    @tag("slow", "docker")
    def test_docker_echo_pandas_dataframe(self):
        """ Notebook that returns a pandas dataframe """
        with self.DockerNotebookRunner(self, "notebook-docker-return-pandas-dataframe.ipynb") as runner:
            # handle should return a pandas dataframe converted to json
            response, json = runner.get_container_response_json("/")

            self.assertIn("data", json)
            data = json["data"]

            self.assertEqual(len(data), 15)  # 15 rows
            self.assertEqual(len(data[0]), 5)  # 5 columns

            # check presence of columns
            self.assertIn("0Seq", data[0])
            self.assertIn("1Rand", data[0])
            self.assertIn("2Nan", data[0])
            self.assertIn("3None", data[0])
            self.assertIn("4Inf", data[0])

            # check order of keys (must maintain original order)
            keys = list(data[5].keys())
            self.assertEqual(keys.index("0Seq"), 0)
            self.assertEqual(keys.index("1Rand"), 1)
            self.assertEqual(keys.index("2Nan"), 2)
            self.assertEqual(keys.index("3None"), 3)
            self.assertEqual(keys.index("4Inf"), 4)

            # check values
            self.assertEqual(data[5]["0Seq"], 5)
            self.assertEqual(data[5]["2Nan"], None)
            self.assertEqual(data[5]["3None"], None)
            self.assertEqual(data[5]["4Inf"], None)

    @tag("slow", "docker")
    def test_docker_custom_library(self):
        """ Notebook that installs a custom library we don't provide and uses it """
        with self.DockerNotebookRunner(self, "notebook-docker-custom-library.ipynb") as runner:
            response, json = runner.get_container_response_json("/")
            self.assertEqual(json["data"], "Hello fuzz: 85")
