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
        response = self.client.post(
            url,
            dict(
                id=notebook_id,
                workspace_id="ws_1",
                title="title: " + notebook_id,
                description="description: " + notebook_id,
                notebook=notebook,
                extra="extra: " + notebook_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data["id"], notebook_id)
        return response

    def update_notebook(self, notebook_id="nb_01", notebook=None, notebook_name=None):
        url = reverse("api:notebook-detail-notebook", args=(notebook_id,))
        if notebook_name:
            url = url + "?name=" + notebook_name
        response = self.client.put(url, data=notebook, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def process_notebook(self, notebook_id="nb_01", query="?async=false", status_code=status.HTTP_200_OK):
        # process notebook synchronously, return response and updated notebook
        url = reverse("api:notebook-job-action", args=(notebook_id, ACTION_PROCESS)) + query
        response = self.client.post(url, format="json")
        data = response.data
        self.assertEqual(response.status_code, status_code)
        if status_code == status.HTTP_200_OK:
            self.assertEqual(data["attributes"]["status"], "completed")

        # retrieve notebook updated with outputs
        url = reverse("api:notebook-detail", args=(notebook_id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response, response.data["attributes"]["notebook"]

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

    def test_notebook_get_notebook_as_json(self):
        """ Gets the jupyter notebook itself rather than the analitico model """
        self.post_notebook("notebook01.ipynb", "nb_01")
        url = reverse("api:notebook-detail-notebook", args=("nb_01",))

        # request as json
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/json")
        notebook = response.data
        self.assertEqual(notebook["cells"][0]["cell_type"], "code")
        self.assertIsNone(notebook["cells"][0]["execution_count"])

    def test_notebook_get_notebook_as_ipynb(self):
        """ Gets the jupyter notebook itself rather than the analitico model """
        self.post_notebook("notebook01.ipynb", "nb_01")
        url = reverse("api:notebook-detail-notebook", args=("nb_01",))

        # request with correct accept for jupyter mime type
        response = self.client.get(url, HTTP_ACCEPT="application/x-ipynb+json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/x-ipynb+json")
        notebook = response.data
        self.assertEqual(notebook["cells"][0]["cell_type"], "code")
        self.assertIsNone(notebook["cells"][0]["execution_count"])

    def test_notebook_get_notebook_as_ipynb_format(self):
        """ Gets the jupyter notebook itself rather than the analitico model """
        self.post_notebook("notebook01.ipynb", "nb_01")
        url = reverse("api:notebook-detail-notebook", args=("nb_01",)) + "?format=ipynb"

        # request with correct accept for jupyter mime type
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/x-ipynb+json")
        notebook = response.data
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
        self.assertEqual("".join(notebook["cells"][1]["outputs"][0]["text"]), "hello world\n")

        self.assertEqual(notebook["metadata"]["kernelspec"]["display_name"], "Python 3")
        self.assertEqual(notebook["metadata"]["kernelspec"]["name"], "python3")
        self.assertEqual(notebook["metadata"]["kernelspec"]["language"], "python")

    def test_notebook_process_twice(self):
        self.post_notebook("notebook01.ipynb", "nb_01")

        _, notebook = self.process_notebook("nb_01")
        self.assertEqual(notebook["cells"][0]["execution_count"], 1)
        self.assertEqual("".join(notebook["cells"][1]["outputs"][0]["text"]), "hello world\n")
        endtime1 = notebook["metadata"]["papermill"]["end_time"]

        _, notebook = self.process_notebook("nb_01")
        self.assertEqual(notebook["cells"][0]["execution_count"], 1)
        self.assertEqual("".join(notebook["cells"][1]["outputs"][0]["text"]), "hello world\n")
        endtime2 = notebook["metadata"]["papermill"]["end_time"]
        self.assertGreater(endtime2, endtime1)

    def test_notebook_process_tags_all(self):
        self.post_notebook("notebook06-tags.ipynb", "nb_06")
        # process entire notebook, no parameters
        response, notebook = self.process_notebook("nb_06", query="?async=False")
        self.assertEqual("".join(notebook["cells"][7]["outputs"][0]["text"]), "Mr. Jack Jr.\n")

    def test_notebook_process_tags_selected(self):
        self.post_notebook("notebook06-tags.ipynb", "nb_06")
        # process only setup and predict cells, no parameters
        response, notebook = self.process_notebook("nb_06", query="?async=False&tags=setup,predict")
        # TODO selective runs
        self.assertEqual("".join(notebook["cells"][7]["outputs"][0]["text"]), "Mr. Jack Jr.\n")

    def test_notebook_save_artifacts(self):
        """ Test a notebook that saves a file which is uploaded as an artifact """
        self.post_notebook("notebook02.ipynb", "nb_02")
        response, notebook = self.process_notebook("nb_02")

        asset = response.data["attributes"]["data"][0]
        self.assertEqual(asset["content_type"], "text/plain")
        self.assertEqual(asset["filename"], "file.txt")
        self.assertEqual(asset["size"], 19)

    def test_notebook_output_formulas_and_graph(self):
        """ Test a notebook that outputs math formulas and plots in various formats """
        self.post_notebook("notebook03.ipynb", "nb_03")
        response, notebook = self.process_notebook("nb_03")
        cells = notebook["cells"]

        # cells[13] has an image of a math formula in various formats
        self.assertEqual(len(cells[13]["outputs"][0]["data"]), 3)
        self.assertIn("image/png", cells[13]["outputs"][0]["data"])
        self.assertIn("text/latex", cells[13]["outputs"][0]["data"])
        self.assertIn("text/plain", cells[13]["outputs"][0]["data"])

        # cells[17] has a chart
        self.assertEqual(len(cells[17]["outputs"][0]["data"]), 1)
        self.assertIn("image/png", cells[13]["outputs"][0]["data"])

        # cells[56] has an html chart
        self.assertEqual(len(cells[56]["outputs"][0]["data"]), 1)
        self.assertIn("text/html", cells[56]["outputs"][0]["data"])

    def test_notebook_output_dataframe(self):
        """ Test a notebook that outputs a pandas dataframe as html table """
        self.post_notebook("notebook04.ipynb", "nb_04")
        response, notebook = self.process_notebook("nb_04")
        cells = notebook["cells"]

        # cells[4] has a table derived from a pandas dataframe
        self.assertEqual(len(cells[4]["outputs"][0]["data"]), 2)
        self.assertIn("text/html", cells[4]["outputs"][0]["data"])
        self.assertIn("text/plain", cells[4]["outputs"][0]["data"])
        self.assertIn("    A   B   C   D   E   F   G   H   I   J\n", cells[4]["outputs"][0]["data"]["text/plain"])

    def test_notebook_convert_html(self):
        """ Convert notebook to html, defaults to full template """
        self.post_notebook("notebook05-rendered.ipynb", "nb_05")
        url = reverse("api:notebook-detail-notebook", args=("nb_05",)) + "?format=html"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response["Content-Type"])
        html = response.content.decode()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<head>", html)
        self.assertIn("Twitter Bootstrap", html)
        self.assertIn("<title>Notebook</title>", html)
        self.assertIn("<body>", html)
        self.assertIn("This Notebook shows how you can add custom display logic", html)
        self.assertIn("image/png", html)
        self.assertIn("</body>", html)

    def test_notebook_convert_html_full_template(self):
        """ Convert notebook to html requesting specifically the 'full' template """
        self.post_notebook("notebook05-rendered.ipynb", "nb_05")
        url = reverse("api:notebook-detail-notebook", args=("nb_05",)) + "?format=html&template=full"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response["Content-Type"])
        html = response.content.decode()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<head>", html)
        self.assertIn("Twitter Bootstrap", html)
        self.assertIn("<title>Notebook</title>", html)
        self.assertIn("<body>", html)
        self.assertIn("This Notebook shows how you can add custom display logic", html)
        self.assertIn("image/png", html)
        self.assertIn("</body>", html)

    def test_notebook_convert_html_basic_template(self):
        """ Convert notebook to html requesting specifically the 'basic' template """
        self.post_notebook("notebook05-rendered.ipynb", "nb_05")
        url = reverse("api:notebook-detail-notebook", args=("nb_05",)) + "?format=html&template=basic"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response["Content-Type"])
        html = response.content.decode()

        # no frills template has no head, just body
        self.assertNotIn("<!DOCTYPE html>", html)
        self.assertNotIn("<head>", html)
        self.assertNotIn("Twitter Bootstrap", html)
        self.assertNotIn("<title>Notebook</title>", html)
        self.assertNotIn("<body>", html)
        self.assertIn("This Notebook shows how you can add custom display logic", html)
        self.assertIn("image/png", html)
        self.assertNotIn("</body>", html)

    def test_notebook_convert_html_bogus_template(self):
        """ Convert notebook to html requesting specifically the 'bogus' template which does not exist """
        self.post_notebook("notebook05-rendered.ipynb", "nb_05")
        url = reverse("api:notebook-detail-notebook", args=("nb_05",)) + "?format=html&template=bogus1"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)  # TODO should be BAD_REQUEST
        self.assertIn("application/json", response["Content-Type"])

        data = response.data
        self.assertEqual(data["error"]["code"], "templatenotfound")
        self.assertEqual(data["error"]["title"], "bogus1")

    def test_notebook_update_patch(self):
        """ Test updating the notebook model, title, description and Jupyter json using PATCH calls """
        response = self.post_notebook("notebook01.ipynb", "nb_01")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        notebook = data["attributes"]["notebook"]

        # update with PATCH on /api/notebooks/id
        notebook1 = notebook
        notebook1["cells"][0]["source"][0] = 'print("hello goofy")'
        data1 = {
            "data": {
                "id": data["id"],
                "attributes": {"title": "title1", "description": "description1", "notebook": notebook1},
            }
        }
        url1 = reverse("api:notebook-detail", args=("nb_01",))
        response1 = self.client.patch(url1, data=data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data["attributes"]["notebook"]["cells"][0]["source"][0], 'print("hello goofy")')
        self.assertEqual(response1.data["attributes"]["title"], "title1")
        self.assertEqual(response1.data["attributes"]["description"], "description1")

        # update, again, with PATCH on /api/notebooks/id
        notebook2 = notebook
        notebook2["cells"][0]["source"][0] = 'print("hello mickey")'
        data2 = {"data": {"id": data["id"], "attributes": {"description": "description2", "notebook": notebook1}}}
        response2 = self.client.patch(url1, data=data2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data["attributes"]["notebook"]["cells"][0]["source"][0], 'print("hello mickey")')
        self.assertEqual(response2.data["attributes"]["title"], "title1")  # unchanged
        self.assertEqual(response2.data["attributes"]["description"], "description2")

    def test_notebook_update_put(self):
        """ Test updating the notebook model, title, description and Jupyter json using PUT calls """
        response = self.post_notebook("notebook01.ipynb", "nb_01")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        notebook = data["attributes"]["notebook"]

        # update with PUT on /api/notebooks/id
        notebook1 = notebook
        notebook1["cells"][0]["source"][0] = 'print("hello goofy")'
        data1 = {
            "data": {
                "id": data["id"],
                "attributes": {
                    "workspace_id": "ws_1",  # TODO required here but not in PATCH, why?
                    "title": "title1",
                    "description": "description1",
                    "notebook": notebook1,
                },
            }
        }
        url1 = reverse("api:notebook-detail", args=("nb_01",))
        response1 = self.client.put(url1, data=data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data["attributes"]["notebook"]["cells"][0]["source"][0], 'print("hello goofy")')
        self.assertEqual(response1.data["attributes"]["title"], "title1")
        self.assertEqual(response1.data["attributes"]["description"], "description1")

        # update, again, with PUT on /api/notebooks/id
        notebook2 = notebook
        notebook2["cells"][0]["source"][0] = 'print("hello mickey")'
        data2 = {
            "data": {
                "id": data["id"],
                "attributes": {
                    "workspace_id": "ws_1",  # TODO required here but not in PATCH, why?
                    "description": "description2",
                    "notebook": notebook1,
                },
            }
        }
        response2 = self.client.put(url1, data=data2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data["attributes"]["notebook"]["cells"][0]["source"][0], 'print("hello mickey")')
        self.assertEqual(response2.data["attributes"]["title"], "title1")  # unchanged
        self.assertEqual(response2.data["attributes"]["description"], "description2")

    def test_notebook_update_notebook(self):
        """ Test updating just the Jupyter json in the notebook model with /api/notebooks/id/notebook endpoint """
        response = self.post_notebook("notebook01.ipynb", "nb_01")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        notebook = data["attributes"]["notebook"]

        # update with PUT on /api/notebooks/id/notebook
        notebook["cells"][0]["source"][0] = 'print("hello goofy")'
        notebook = self.update_notebook("nb_01", notebook)
        self.assertEqual(notebook["cells"][0]["source"][0], 'print("hello goofy")')

        # update, again, with PUT on /api/notebooks/id/notebook
        notebook["cells"][0]["source"][0] = 'print("hello mickey")'
        notebook = self.update_notebook("nb_01", notebook)
        self.assertEqual(notebook["cells"][0]["source"][0], 'print("hello mickey")')

        # update, again, with PUT on /api/notebooks/id/notebook and { "data": xxx } wrapping a la json:api
        notebook["cells"][0]["source"][0] = 'print("hello donald")'
        notebook = self.update_notebook("nb_01", {"data": notebook})
        self.assertEqual(notebook["cells"][0]["source"][0], 'print("hello donald")')

    def test_notebook_raise_exception(self):
        # Run a notebook containing a single cell that raises an Exception
        self.post_notebook("notebook09.ipynb", "nb_09")
        _, notebook = self.process_notebook("nb_09", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # notebook was NOT executed correctly, it raised an exception!
        self.assertEqual(notebook["metadata"]["papermill"]["exception"], True)

        # first cell was created by papermill because the notebook raised an exception
        self.assertEqual(notebook["cells"][0]["cell_type"], "code")
        self.assertEqual(notebook["cells"][0]["execution_count"], None)
        self.assertEqual(notebook["cells"][0]["metadata"]["hide_input"], True)
        self.assertEqual(notebook["cells"][0]["metadata"]["inputHidden"], True)
        cell_html = "".join(notebook["cells"][0]["outputs"][0]["data"]["text/html"])
        self.assertTrue("An Exception was encountered" in cell_html)

        # second cell contains parameters inserted by papermill
        self.assertEqual(notebook["cells"][1]["cell_type"], "code")
        self.assertEqual(notebook["cells"][1]["execution_count"], 1)

        # third cell is the only one we wrote that contained the code raising the exception
        self.assertEqual(notebook["cells"][2]["cell_type"], "code")
        self.assertEqual(notebook["cells"][2]["execution_count"], 2)
        self.assertEqual(notebook["cells"][2]["metadata"]["papermill"]["exception"], True)
        self.assertEqual(notebook["cells"][2]["metadata"]["papermill"]["status"], "failed")

    def test_notebook_raise_exception_run_repeatedly(self):
        # Run a notebook containing a single cell a few times, check that it doesn't create extra error cells
        self.post_notebook("notebook09.ipynb", "nb_09")

        # notebook was NOT executed correctly, it raised an exception!
        _, notebook = self.process_notebook("nb_09", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(notebook["metadata"]["papermill"]["exception"], True)
        self.assertEqual(len(notebook["cells"]), 3)

        # run for a second time (the error cell at the top was removed and the added again)
        _, notebook = self.process_notebook("nb_09", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(notebook["metadata"]["papermill"]["exception"], True)
        self.assertEqual(len(notebook["cells"]), 3)

        # run for a third time (the error cell at the top was removed and the added again)
        _, notebook = self.process_notebook("nb_09", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(notebook["metadata"]["papermill"]["exception"], True)
        self.assertEqual(len(notebook["cells"]), 3)

        # third cell is the only one we wrote that contained the code raising the exception
        self.assertEqual(notebook["cells"][2]["cell_type"], "code")
        self.assertEqual(notebook["cells"][2]["execution_count"], 2)
        self.assertEqual(notebook["cells"][2]["metadata"]["papermill"]["exception"], True)
        self.assertEqual(notebook["cells"][2]["metadata"]["papermill"]["status"], "failed")
