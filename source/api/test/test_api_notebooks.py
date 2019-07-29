import os
import os.path
import json
import pytest

from django.urls import reverse
from rest_framework import status

# conflicts with django's dynamically generated model.objects

# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

from analitico.constants import ACTION_PROCESS
from analitico.utilities import read_json

from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import AnaliticoApiTestCase

NOTEBOOKS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/notebooks/"


@pytest.mark.django_db
class NotebooksTests(AnaliticoApiTestCase):
    """ Test notebooks operations via APIs """

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

    def test_notebook_process_with_exception(self):
        self.post_notebook("notebook12-with-exception.ipynb", "nb_12")

        # notebook will raise an exception and stop being processed
        url = reverse("api:notebook-job-action", args=("nb_12", ACTION_PROCESS)) + "?async=false"
        response = self.client.post(url, format="json")
        data = response.data
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            data["error"]["title"],
            "An error occoured while running nb_12: Notebook wants to fail and raised an exception",
        )

    def test_notebook_process_with_missing_import(self):
        self.post_notebook("notebook13-with-missing-import.ipynb", "nb_13")

        # notebook includes some import for libraries that cannot be found
        url = reverse("api:notebook-job-action", args=("nb_13", ACTION_PROCESS)) + "?async=false"
        response = self.client.post(url, format="json")
        data = response.data
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            data["error"]["title"],
            "An error occoured while running nb_13: No module named 'themissinglibrarythatdoesntexist'",
        )

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
                    "workspace_id": "ws_001",  # TODO required here but not in PATCH, why?
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
                    "workspace_id": "ws_001",  # TODO required here but not in PATCH, why?
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

    def test_notebook_process_with_logs(self):
        """ Process a notebook and capture its logs """
        self.post_notebook("notebook10.ipynb", "nb_01")

        # process notebook synchronously
        url = reverse("api:notebook-job-action", args=("nb_01", ACTION_PROCESS)) + "?async=false"
        response = self.client.post(url, format="json")
        data = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["attributes"]["status"], "completed")

        # job contains logs from execution of notebook inside papermill
        logs = data["attributes"]["logs"]
        self.assertIn("Executing Cell 1-------", logs)
        self.assertIn("Hello papermill\n", logs)
        self.assertIn("Executing Cell 2-------", logs)

    def test_notebook_raise_exception_with_logs(self):
        # Run a notebook containing a cell that raises an exception, check if excption listed in the job
        self.post_notebook("notebook09.ipynb", "nb_09")

        # job should not execute correctly and should contain errors generated within the notebook
        url = reverse("api:notebook-job-action", args=("nb_09", ACTION_PROCESS)) + "?async=false"
        response = self.client.post(url, format="json")
        job_id = response.data["error"]["meta"]["extra"]["job_id"]

        # retrieve the failed job
        url = reverse("api:job-detail", args=(job_id,))
        job = self.client.get(url).data

        # job should contain error output from the failed cell
        self.assertEqual(job["attributes"]["errors"][0]["cell_index"], 0)
        self.assertEqual(job["attributes"]["errors"][0]["ename"], "Exception")
        self.assertEqual(job["attributes"]["errors"][0]["evalue"], "The notebook raised this TEST exception")
        self.assertEqual(job["attributes"]["errors"][0]["output_type"], "error")

    def test_notebook_generate_dataset(self):
        # Run a notebook that generates a dataset with a variable number of rows
        self.post_notebook("notebook14-generate-dataset.ipynb", "nb_14")
        nb = Notebook.objects.get(pk="nb_14")

        ##
        ## number of rows is not specified (will do default of 100 rows)
        ##
        nb_out1 = api.models.notebook.nb_run(
            notebook_item=nb, notebook_name=None, factory=factory, upload=True, job=None
        )

        # updated metadata and assets
        nb = Notebook.objects.get(pk="nb_14")
        assets = nb.get_attribute("data")

        # check number of rows
        pandas_csv = next(asset for asset in assets if asset["id"] == "pandas.csv")
        self.assertEqual(pandas_csv["rows"], 100)
        data_csv = next(asset for asset in assets if asset["id"] == "data.csv")
        self.assertEqual(data_csv["rows"], 100)
        self.assertEqual(data_csv["schema"]["columns"][0]["name"], "A_100")

        ##
        ## now we specify a parameter indicating that we want 500 rows
        ##
        nb_out2 = api.models.notebook.nb_run(
            notebook_item=nb, notebook_name=None, factory=factory, upload=True, parameters={"rows": "500"}
        )

        # updated metadata and assets
        nb = Notebook.objects.get(pk="nb_14")
        assets = nb.get_attribute("data")

        # check number of rows, schema updates
        pandas_csv = next(asset for asset in assets if asset["id"] == "pandas.csv")
        self.assertEqual(pandas_csv["rows"], 500)

        data_csv = next(asset for asset in assets if asset["id"] == "data.csv")
        self.assertEqual(data_csv["rows"], 500)
        self.assertEqual(data_csv["schema"]["columns"][0]["name"], "A_500")

        ##
        ## now we specify a parameter indicating that we want 90 rows
        ##
        nb_out2 = api.models.notebook.nb_run(
            notebook_item=nb, notebook_name=None, factory=factory, upload=True, parameters={"rows": "90"}
        )

        # updated metadata and assets
        nb = Notebook.objects.get(pk="nb_14")
        assets = nb.get_attribute("data")

        # check number of rows
        pandas_csv = next(asset for asset in assets if asset["id"] == "pandas.csv")
        self.assertEqual(pandas_csv["rows"], 90)
        data_csv = next(asset for asset in assets if asset["id"] == "data.csv")
        self.assertEqual(data_csv["rows"], 90)
        self.assertEqual(data_csv["schema"]["columns"][0]["name"], "A_90")

        ##
        ## now we specify NO parameter again and it should go back to 100
        ##
        nb_out2 = api.models.notebook.nb_run(notebook_item=nb, notebook_name=None, factory=factory, upload=True)

        # updated metadata and assets
        nb = Notebook.objects.get(pk="nb_14")
        assets = nb.get_attribute("data")

        # check number of rows
        pandas_csv = next(asset for asset in assets if asset["id"] == "pandas.csv")
        self.assertEqual(pandas_csv["rows"], 100)
        data_csv = next(asset for asset in assets if asset["id"] == "data.csv")
        self.assertEqual(data_csv["rows"], 100)
        self.assertEqual(data_csv["schema"]["columns"][0]["name"], "A_100")
