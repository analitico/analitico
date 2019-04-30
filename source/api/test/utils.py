import os
import os.path

from rest_framework.test import APITestCase

from rest_framework import status

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from api.models import Token, User, Workspace
from analitico.utilities import read_json, get_dict_dot

# pylint: disable=no-member

import logging

logger = logging.getLogger("analitico")

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets/"
NOTEBOOKS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/notebooks/"


class APITestCase(APITestCase):
    """ Base class for testing analitico APIs """

    def read_json_asset(self, path):
        abs_path = os.path.join(ASSETS_PATH, path)
        return read_json(abs_path)

    def read_notebook_asset(self, path):
        abs_path = os.path.join(NOTEBOOKS_PATH, path)
        return read_json(abs_path)

    def get_asset_path(self, asset_name):
        return os.path.join(ASSETS_PATH, asset_name)

    def get_items(self, item_type, token=None, status_code=status.HTTP_200_OK):
        url = reverse("api:" + item_type[len] + "-list")
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

    def upload_file(self, url, asset_name, content_type, token=None, status_code=status.HTTP_201_CREATED):
        """ Uploads a single asset to given url service, performs basic checks """
        asset_path = asset_name
        if not os.path.isfile(asset_name):
            asset_path = os.path.join(ASSETS_PATH, asset_name)
        asset_size = os.path.getsize(asset_path)
        with open(asset_path, "rb") as asset_file:

            asset_data = asset_file.read()
            asset_uploaded = SimpleUploadedFile(asset_name, asset_data, content_type)

            data = {"file": asset_uploaded}
            # no token means no authentication, not use default token
            self.auth_token(token)
            response = self.client.post(url, data, format="multipart")
            self.assertEqual(response.status_code, status_code)

            if status_code == status.HTTP_201_CREATED:
                self.assertEqual(len(response.data), 1)
                data = response.data[0]
                self.assertEqual(data["content_type"], content_type)
                self.assertTrue(data["filename"] in asset_name)
                self.assertEqual(data["size"], asset_size)
            return response

    def setup_basics(self):
        self.user1 = User.objects.create_user(
            email="user1@analitico.ai", is_staff=True, is_superuser=True
        )  # 1st user is admin
        self.user2 = User.objects.create_user(email="user2@analitico.ai")  # 2nd is a regular user
        self.user3 = User.objects.create_user(email="user3@analitico.ai")  # 3rd is a regular user
        self.user4 = User.objects.create_user(email="user4@analitico.ai", is_staff=True)  # 4th is staff but not admin

        self.token1 = Token.objects.create(pk="tok_user1", user=self.user1)
        self.token2 = Token.objects.create(pk="tok_user2", user=self.user2)
        self.token3 = Token.objects.create(pk="tok_user3", user=self.user3)
        self.token4 = Token.objects.create(pk="tok_user4", user=self.user4)

        self.ws1 = Workspace.objects.create(pk="ws_user1", user=self.user1)
        self.ws2 = Workspace.objects.create(pk="ws_user2", user=self.user2)
        self.ws3 = Workspace.objects.create(pk="ws_user3", user=self.user3)
        self.ws4 = Workspace.objects.create(pk="ws_user4", user=self.user4)

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
