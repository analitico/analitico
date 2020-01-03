import os
import os.path
import pytest

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from analitico import ACTION_PROCESS
from api.models import Token, User, Workspace, Drive, NOTEBOOK_MIME_TYPE
from analitico.utilities import read_json, get_dict_dot

# pylint: disable=no-member

import logging

logger = logging.getLogger("analitico")

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets/"
NOTEBOOKS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/notebooks/"
UNICORN_FILENAME = "unicorns-do-it-better.png"


@pytest.mark.django_db
class AnaliticoApiTestCase(APITestCase):
    """ Base class for testing analitico APIs """

    def get_storage_conf(self):
        """ Configuration for the storage box for testing """
        return {
            "storage": {
                "hold": True,
                "driver": "hetzner-webdav",
                "storagebox_id": "196299",
                "url": "https://u208199.your-storagebox.de",
                "credentials": {"username": "u208199", "password": "AyG9OxeeuXr0XpqF"},
            }
        }

    def assertApiResponse(self, response, status_code=status.HTTP_200_OK):
        """ Assert that the response has succeded and contains "data" """
        if response.status_code != status_code:
            logger.warn(f"response.status_code: {response.status_code}; was expecting: {status_code}")
            logger.warn(f"response.content: {str(response.content)}")
        self.assertEqual(response.status_code, status_code)

    def read_json_asset(self, path):
        abs_path = os.path.join(ASSETS_PATH, path)
        return read_json(abs_path)

    def read_notebook_asset(self, path):
        abs_path = os.path.join(NOTEBOOKS_PATH, path)
        return read_json(abs_path)

    def get_asset_path(self, asset_name):
        return os.path.join(ASSETS_PATH, asset_name)

    def get_items(self, item_type, token=None, status_code=status.HTTP_200_OK):
        url = reverse("api:" + item_type + "-list")
        self.auth_token(token)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status_code)
        if response.status_code == status.HTTP_200_OK:
            self.assertIsNotNone(response.data)
        return response.data

    def get_item(self, item_type, item_id, token=None, status_code=status.HTTP_200_OK, query=None):
        url = reverse("api:" + item_type + "-detail", args=(item_id,))
        if query:
            url += query
        self.auth_token(token)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status_code)
        if response.status_code == status.HTTP_200_OK:
            self.assertIsNotNone(response.data)
        return response.data

    def patch_item(self, item_type, item_id, item, token=None, status_code=status.HTTP_200_OK):
        url = reverse("api:" + item_type + "-detail", args=(item_id,))
        self.auth_token(token)
        response = self.client.patch(url, item, format="json")
        self.assertEqual(response.status_code, status_code)
        return response.data

    def delete_item(self, item_type, item_id, token=None, status_code=status.HTTP_200_OK):
        url = reverse("api:" + item_type + "-detail", args=(item_id,))
        self.auth_token(token)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status_code)
        return response.data

    def upload_items(self, endpoint, prefix):
        try:
            for path in os.listdir(ASSETS_PATH):
                if not os.path.isdir(os.path.join(ASSETS_PATH, path)):
                    if path.startswith(prefix):
                        item = self.read_json_asset(path)
                        # print("Loading {}:{} from {}...".format(item["type"], item["id"], path))

                        token = self.token1
                        if get_dict_dot(item, "attributes.user") == "user2@analitico.ai":
                            token = self.token2
                        if get_dict_dot(item, "attributes.user") == "user3@analitico.ai":
                            token = self.token3

                        self.auth_token(token)
                        response = self.client.post(endpoint, {"data": item}, format="json")
                        self.assertIsNotNone(response.data)

                        created_item = response.data
                        self.assertFalse("error" in created_item, "Error should not be in response")
                        self.assertEqual(item["id"], created_item["id"])
                        self.assertEqual(item["type"], created_item["type"])
                        self.assertEqual(item["attributes"]["title"], created_item["attributes"]["title"])
                        self.assertEqual(item["attributes"]["description"], created_item["attributes"]["description"])
        except Exception as exc:
            raise exc

    def auth_token(self, token=None):
        """ Append authorization token to self.client calls """
        if token is not None:
            self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token.id)
        else:
            self.client.logout()

    def upload_file(self, url, asset_name, content_type, token=None, status_code=None):
        """ Uploads a single asset to given url service, performs basic checks """
        asset_path = asset_name
        if not os.path.isfile(asset_name):
            asset_path = os.path.join(ASSETS_PATH, asset_name)
        with open(asset_path, "rb") as asset_file:

            asset_data = asset_file.read()
            asset_uploaded = SimpleUploadedFile(asset_name, asset_data, content_type)
            data = {"file": asset_uploaded}

            # no token means no authentication, not use default token
            self.auth_token(token)
            response = self.client.post(url, data, format="multipart")
            if status_code:
                self.assertEqual(response.status_code, status_code)
            else:
                self.assertTrue(
                    response.status_code == status.HTTP_201_CREATED
                    or response.status_code == status.HTTP_204_NO_CONTENT
                )
            return response

    def upload_unicorn(self, item=None, token=None):
        """ The same image is used in a number of tests """
        if item is None:
            item = self.ws1
        url = reverse(f"api:{item.type}-files", args=(item.id, UNICORN_FILENAME))
        response = self.upload_file(url, UNICORN_FILENAME, "image/png", token=token if token else self.token1)
        return url, response

    def setup_basics(self):
        # test users
        self.user1 = User.objects.create_user(
            email="user1@analitico.ai", is_staff=True, is_superuser=True
        )  # 1st user is admin
        self.user2 = User.objects.create_user(email="user2@analitico.ai")  # 2nd is a regular user
        self.user3 = User.objects.create_user(email="user3@analitico.ai")  # 3rd is a regular user
        self.user4 = User.objects.create_user(email="user4@analitico.ai", is_staff=True)  # 4th is staff but not admin

        # test tokens
        self.token1 = Token.objects.create(pk="tok_user1", user=self.user1)
        self.token2 = Token.objects.create(pk="tok_user2", user=self.user2)
        self.token3 = Token.objects.create(pk="tok_user3", user=self.user3)
        self.token4 = Token.objects.create(pk="tok_user4", user=self.user4)

        # test workspaces
        ws1 = self.read_json_asset(os.path.join(ASSETS_PATH, "ws_001.json"))
        ws2 = self.read_json_asset(os.path.join(ASSETS_PATH, "ws_002.json"))
        ws3 = self.read_json_asset(os.path.join(ASSETS_PATH, "ws_003.json"))
        ws_storage_webdav = self.read_json_asset(os.path.join(ASSETS_PATH, "ws_storage_webdav.json"))
        ws_gallery = self.read_json_asset(os.path.join(ASSETS_PATH, "ws_gallery.json"))

        endpoint = reverse("api:workspace-list")
        self.auth_token(self.token1)
        response_ws1 = self.client.post(endpoint, {"data": ws1}, format="json")
        self.assertEqual(response_ws1.status_code, status.HTTP_201_CREATED)
        self.auth_token(self.token2)
        response_ws2 = self.client.post(endpoint, {"data": ws2}, format="json")
        self.assertEqual(response_ws2.status_code, status.HTTP_201_CREATED)
        self.auth_token(self.token3)
        response_ws3 = self.client.post(endpoint, {"data": ws3}, format="json")
        self.assertEqual(response_ws3.status_code, status.HTTP_201_CREATED)
        self.auth_token(self.token1)
        response_ws_storage_webdav = self.client.post(endpoint, {"data": ws_storage_webdav}, format="json")
        self.assertEqual(response_ws_storage_webdav.status_code, status.HTTP_201_CREATED)
        self.auth_token(self.token1)
        response_ws_gallery = self.client.post(endpoint, {"data": ws_gallery}, format="json")
        self.assertEqual(response_ws_gallery.status_code, status.HTTP_201_CREATED)
        self.client.logout()

        self.ws1 = Workspace.objects.get(pk=response_ws1.data["id"])
        self.ws2 = Workspace.objects.get(pk=response_ws2.data["id"])
        self.ws3 = Workspace.objects.get(pk=response_ws3.data["id"])
        self.ws_storage_webdav = Workspace.objects.get(pk=response_ws_storage_webdav.data["id"])
        self.ws_gallery = Workspace.objects.get(pk=response_ws_gallery.data["id"])

        # test drive
        self.drive = Drive(id="dr_box002_test", attributes=self.get_storage_conf())
        self.drive.save()

    def assertStatusCode(self, response, status_code=status.HTTP_200_OK):
        if response.status_code != status_code:
            logger.error(
                "Response status_code should be {} but instead it is {}\nResponse is: {}".format(
                    status_code, response.status_code, response.content
                )
            )
        self.assertEqual(response.status_code, status_code)

    def setUp(self):
        """ Prepare test users with test auth tokens """
        self.setup_basics()

    ##
    ## Notebooks
    ##

    def read_notebook(self, notebook_path):
        if not os.path.isfile(notebook_path):
            notebook_path = os.path.join(NOTEBOOKS_PATH, notebook_path)
            assert os.path.isfile(notebook_path)
        return read_json(notebook_path)

    def post_notebook(self, notebook_path, notebook_id="nb_1", notebook_name="notebook.ipynb"):
        """ Posts a notebook model """
        if not os.path.isfile(notebook_path):
            notebook_path = os.path.join(NOTEBOOKS_PATH, notebook_path)
            assert os.path.isfile(notebook_path)
        notebook = self.read_notebook(notebook_path)

        url = reverse("api:notebook-list")
        self.auth_token(token=self.token1)
        response = self.client.post(
            url,
            dict(
                id=notebook_id,
                workspace_id="ws_001",
                title="title: " + notebook_id,
                description="description: " + notebook_id,
                notebook=notebook,
                extra="extra: " + notebook_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # upload notebook file
        url = reverse("api:notebook-files", args=(notebook_id, notebook_name))
        response_upload = self.upload_file(url, notebook_path, NOTEBOOK_MIME_TYPE, token=self.token1)
        self.assertEqual(response_upload.status_code, status.HTTP_204_NO_CONTENT)

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
