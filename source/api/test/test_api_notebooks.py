import os
import os.path
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

from analitico.constants import ACTION_PROCESS
from analitico.utilities import read_json

from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import APITestCase

NOTEBOOKS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/notebooks/"


class NotebooksTests(APITestCase):
    """ Test notebooks operations via APIs """

    def read_notebook(self, notebook_path):
        if not os.path.isfile(notebook_path):
            notebook_path = os.path.join(NOTEBOOKS_PATH, notebook_path)
            assert os.path.isfile(notebook_path)
        return read_json(notebook_path)

    def post_notebook(self, notebook_path, notebook_id="nb_1"):
        """ Posts a notebook model """
        notebook = self.read_notebook(notebook_path)

        url = reverse("api:notebook-list")
        self.auth_token(token=self.token1)
        response = self.client.post(url, dict(id=notebook_id, workspace_id="ws_1", notebook=notebook), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data["id"], notebook_id)
        return response

    def setUp(self):
        self.setup_basics()
        ws_01 = Workspace(id="ws_1", user=self.user1)
        ws_01.save()
        ws_02 = Workspace(id="ws_2", user=self.user1)
        ws_02.save()

    def test_notebook_post(self):
        response = self.post_notebook("notebook01.ipynb", "nb_01")
        notebook = response.data["attributes"]["notebook"]
        self.assertEqual(notebook["cells"][0]["cell_type"], "code")
        self.assertIsNone(notebook["cells"][0]["execution_count"])

    def test_notebook_get(self):
        self.post_notebook("notebook01.ipynb", "nb_01")
        url = reverse("api:notebook-detail", args=("nb_01",))
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notebook = response.data["attributes"]["notebook"]
        self.assertEqual(notebook["cells"][0]["cell_type"], "code")
        self.assertIsNone(notebook["cells"][0]["execution_count"])

    def test_notebook_get_norights(self):
        self.post_notebook("notebook01.ipynb", "nb_01")
        url = reverse("api:notebook-detail", args=("nb_01",))
        self.auth_token(self.token2)
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notebook_get_notebook(self):
        """ Gets the jupyter notebook itself rather than the analitico model """
        self.post_notebook("notebook01.ipynb", "nb_01")
        url = reverse("api:notebook-detail-notebook", args=("nb_01",))
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], NOTEBOOK_MIME_TYPE)
        notebook = json.loads(response.content)

        self.assertEqual(notebook["cells"][0]["cell_type"], "code")
        self.assertIsNone(notebook["cells"][0]["execution_count"])

    def test_notebook_process(self):
        self.post_notebook("notebook01.ipynb", "nb_01")

        # process notebook synchronously
        url = reverse("api:notebook-job-action", args=("nb_01", ACTION_PROCESS)) + "?async=false"
        response = self.client.post(url, format="json")
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["attributes"]["status"], "completed")

        # notebook was executed and produced "hello world\n" as output which was saved in outputs
        notebook_url = reverse("api:notebook-detail", args=("nb_01",))
        response = self.client.get(notebook_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notebook = response.data["attributes"]["notebook"]
        self.assertEqual(notebook["cells"][0]["cell_type"], "code")
        self.assertEqual(notebook["cells"][0]["execution_count"], 1)
        self.assertEqual(notebook["cells"][1]["outputs"][0]["text"][0], "hello world\n")
