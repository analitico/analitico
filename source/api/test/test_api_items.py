import os
import numpy as np
import math

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from analitico.utilities import get_dict_dot, time_ms

import analitico
import api.models

from analitico import logger
from api.models import Workspace
from .utils import AnaliticoApiTestCase

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets/"


class ItemsTests(AnaliticoApiTestCase):
    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:dataset-list")
            self.upload_items(url, analitico.DATASET_PREFIX)

        except Exception as exc:
            print(exc)
            raise exc

    def test_items_default_id_prefix(self):
        """ Test models to make sure they are created with the correct prefix in their IDs """
        item = api.models.Dataset()
        self.assertTrue(item.id.startswith(analitico.DATASET_PREFIX))
        item = api.models.Endpoint()
        self.assertTrue(item.id.startswith(analitico.ENDPOINT_PREFIX))
        item = api.models.Job()
        self.assertTrue(item.id.startswith(analitico.JOB_PREFIX))
        item = api.models.Model()
        self.assertTrue(item.id.startswith(analitico.MODEL_PREFIX))
        item = api.models.Recipe()
        self.assertTrue(item.id.startswith(analitico.RECIPE_PREFIX))
        item = api.models.Workspace()
        self.assertTrue(item.id.startswith(analitico.WORKSPACE_PREFIX))

    ##
    ## Workspace
    ##

    def test_workspace_get(self):
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_001", self.token1)
        self.assertEqual(item["id"], "ws_001")
        self.assertEqual(item["attributes"]["user"], "user1@analitico.ai")
        self.assertEqual(item["attributes"]["title"], "Workspace1")
        self.assertEqual(item["attributes"]["description"], "This is the description")

    def test_workspace_get_user2(self):
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_002", self.token1)
        self.assertEqual(item["id"], "ws_002")
        self.assertEqual(item["attributes"]["user"], "user2@analitico.ai")
        self.assertEqual(item["attributes"]["title"], "Workspace2")
        self.assertEqual(item["attributes"]["description"], "This is the description")

    def test_workspace_get_without_authorization(self):
        # user2 is not the owner of this workspace so, altough it does exist,
        # the server should pretend it's not there (which it isn't for this user)
        # and return an item not found code of HTTP 404
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_001", self.token2, status_code=status.HTTP_404_NOT_FOUND)
        self.assertEqual(item["error"]["code"], "not_found")
        self.assertIsNotNone(item["error"]["title"])
        self.assertEqual(item["error"]["status"], "404")  # a string, not a number

    def test_workspace_get_without_authorization_as_admin(self):
        # ws_002 is owned by user2@analitico.ai but user1 is an admin so he should get it
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_002", self.token1)
        self.assertEqual(item["id"], "ws_002")
        self.assertEqual(item["attributes"]["title"], "Workspace2")
        self.assertEqual(item["attributes"]["description"], "This is the description")

    def test_workspace_patch_title(self):
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_001", self.token1)
        self.assertEqual(item["id"], "ws_001")
        self.assertEqual(item["attributes"]["title"], "Workspace1")
        self.assertEqual(item["attributes"]["description"], "This is the description")

        patch = {"data": {"id": "ws_001", "attributes": {"title": "This is the patched title"}}}
        patch_item = self.patch_item(analitico.WORKSPACE_TYPE, "ws_001", patch, self.token1)
        self.assertEqual(patch_item["attributes"]["title"], "This is the patched title")
        self.assertEqual(patch_item["attributes"]["description"], "This is the description")

    def test_workspace_patch_title_user2(self):
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_002", self.token1)
        self.assertEqual(item["id"], "ws_002")
        self.assertEqual(item["attributes"]["title"], "Workspace2")
        self.assertEqual(item["attributes"]["description"], "This is the description")

        patch = {"data": {"id": "ws_002", "attributes": {"title": "This is the patched title"}}}
        patch_item = self.patch_item(analitico.WORKSPACE_TYPE, "ws_002", patch, self.token1)
        self.assertEqual(patch_item["attributes"]["title"], "This is the patched title")
        self.assertEqual(patch_item["attributes"]["description"], "This is the description")

    def test_workspace_patch_item_patch_title_without_authorization(self):
        patch = {"data": {"id": "ws_001", "attributes": {"title": "This is the patched title"}}}
        # user2 is not the owner of this workspace so, altough it does exist,
        # the server should pretend it's not there (which it isn't for this user)
        # and return an item not found code of HTTP 404
        patch_item = self.patch_item(
            analitico.WORKSPACE_TYPE, "ws_001", patch, self.token2, status_code=status.HTTP_404_NOT_FOUND
        )
        self.assertEqual(patch_item["error"]["code"], "not_found")
        self.assertIsNotNone(patch_item["error"]["title"])
        self.assertEqual(patch_item["error"]["status"], "404")  # a string, not a number

    def test_workspace_patch_made_up_attribute(self):
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_001", self.token1)
        self.assertEqual(item["id"], "ws_001")
        self.assertEqual(item["attributes"]["title"], "Workspace1")
        self.assertEqual(item["attributes"]["description"], "This is the description")
        self.assertFalse("made_up_attribute" in item["attributes"])

        patch = {"data": {"id": "ws_001", "attributes": {"made_up_attribute": "This is a made up attribute"}}}
        patch_item = self.patch_item(analitico.WORKSPACE_TYPE, "ws_001", patch, self.token1)
        self.assertEqual(patch_item["attributes"]["title"], "Workspace1")
        self.assertEqual(patch_item["attributes"]["description"], "This is the description")
        self.assertEqual(patch_item["attributes"]["made_up_attribute"], "This is a made up attribute")

    def test_workspace_patch_made_up_attribute_with_children(self):
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_001", self.token1)
        self.assertEqual(item["id"], "ws_001")
        self.assertEqual(item["attributes"]["title"], "Workspace1")
        self.assertEqual(item["attributes"]["description"], "This is the description")
        self.assertFalse("made_up_attribute" in item["attributes"])

        patch = {
            "data": {
                "id": "ws_001",
                "attributes": {
                    "made_up_attribute_two": {
                        "child1": "This is a made up attribute, child 1",
                        "child2": "This is a made up attribute, child 2",
                    },
                    "made_up_attribute_three": "This is made_up_attribute_three",
                },
            }
        }
        patch_item = self.patch_item(analitico.WORKSPACE_TYPE, "ws_001", patch, self.token1)
        self.assertEqual(patch_item["attributes"]["title"], "Workspace1")
        self.assertEqual(patch_item["attributes"]["description"], "This is the description")
        self.assertEqual(
            patch_item["attributes"]["made_up_attribute_two"]["child1"], "This is a made up attribute, child 1"
        )
        self.assertEqual(
            patch_item["attributes"]["made_up_attribute_two"]["child2"], "This is a made up attribute, child 2"
        )
        self.assertEqual(patch_item["attributes"]["made_up_attribute_three"], "This is made_up_attribute_three")

    def test_workspace_patch_change_remove(self):
        patch = {"data": {"id": "ws_001", "attributes": {"made_up_attribute": "adding something"}}}
        patch_item = self.patch_item(analitico.WORKSPACE_TYPE, "ws_001", patch, self.token1)
        self.assertEqual(patch_item["attributes"]["made_up_attribute"], "adding something")

        patch["data"]["attributes"]["made_up_attribute"] = "then changing it"
        patch_item = self.patch_item(analitico.WORKSPACE_TYPE, "ws_001", patch, self.token1)
        self.assertEqual(patch_item["attributes"]["made_up_attribute"], "then changing it")

        patch["data"]["attributes"]["made_up_attribute"] = None  # them removing it
        patch_item = self.patch_item(analitico.WORKSPACE_TYPE, "ws_001", patch, self.token1)
        self.assertIsNone(patch_item["attributes"].get("made_up_attribute"))

    def test_workspace_delete(self):
        item = self.delete_item(analitico.WORKSPACE_TYPE, "ws_001", self.token1, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(item)

        # no try and get deleted item, should return a 404
        item = self.delete_item(analitico.WORKSPACE_TYPE, "ws_001", self.token1, status.HTTP_404_NOT_FOUND)
        self.assertEqual(item["error"]["code"], "not_found")
        self.assertIsNotNone(item["error"]["title"])
        self.assertEqual(item["error"]["status"], "404")  # a string, not a number

    def test_workspace_delete_without_authorization(self):
        # user2 is not the owner of this workspace so, altough it does exist,
        # the server should pretend it's not there (which it isn't for this user)
        # and return an item not found code of HTTP 404
        item = self.delete_item(analitico.WORKSPACE_TYPE, "ws_001", self.token2, status_code=status.HTTP_404_NOT_FOUND)
        self.assertEqual(item["error"]["code"], "not_found")
        self.assertIsNotNone(item["error"]["title"])
        self.assertEqual(item["error"]["status"], "404")  # a string, not a number

    def test_workspace_delete_without_authorization_as_admin(self):
        # ws_002 is owned by user2@analitico.ai but user1 is an admin so he should be able to delete it
        item = self.delete_item(
            analitico.WORKSPACE_TYPE, "ws_002", token=self.token1, status_code=status.HTTP_204_NO_CONTENT
        )
        self.assertIsNone(item)

    ##
    ## NaN and sanitization of attributes
    ##

    def test_workspace_apply_nan_attribute(self):
        """ Add np.NaN to an attribute and make sure the item can be serialized and deserialized """
        ws = Workspace.objects.get(pk="ws_001")
        ws.set_attribute("mickey", np.NaN)
        ws.save()

        # retrieve item containing NaN
        item = self.get_item(analitico.WORKSPACE_TYPE, "ws_001", self.token1)
        self.assertTrue(math.isnan(item["attributes"]["mickey"]))  # regular python nan, not a numpy nan

    ##
    ## Avatar
    ##

    # test avatar square

    # test avatar width

    # test avatar height

    # test avatar width and height

    # test avatar nothing specified

    # test avatar with default

    # test avatar with wrong or non available image

    ##
    ## Cloning items
    ##

    def create_item_then_clone_it(self, item_class, workspace_id=None):
        started_on = time_ms()
        item = None
        clone = None
        try:
            item = item_class(workspace=self.ws1)
            item.save()

            # create some files in a few directories
            for i in range(0, 16):
                if i < 12:
                    path = f"tst_dir_{int(i/3)}/tst_file_{i}.txt"
                else:
                    path = f"tst_file_{i}.txt"
                url = reverse(f"api:{item.type}-files", args=(item.id, path))
                response = self.client.put(url, b"A simple string", content_type="text/simple")

            # retrieve list of files in item
            item_files_url = reverse(f"api:{item.type}-files", args=(item.id, ""))
            item_files = self.client.get(item_files_url + "?metadata=true").data
            self.assertEqual(len(item_files), 8 + 1)

            # call API to clone item and /files
            url = reverse(f"api:{item.type}-clone", args=(item.id,))
            if workspace_id:
                url += "?workspace_id=" + workspace_id
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            clone_id = response.data["id"]
            clone = api.factory.factory.get_item(clone_id)

            # get list of file assets for cloned item (should match the ones we created)
            clone_files_url = reverse(f"api:{clone.type}-files", args=(clone.id, ""))
            clone_files = self.client.get(clone_files_url + "?metadata=true").data

            self.assertEqual(len(item_files), len(clone_files))
            for i in range(0, len(item_files)):
                self.assertEqual(item_files[i]["id"], clone_files[i]["id"])

            self.assertEqual(clone.workspace.id, workspace_id if workspace_id else item.workspace.id)
            self.assertEqual(item.type, clone.type)
            self.assertNotEqual(item.id, clone.id)

        finally:
            logger.info(f"\ncreate_item_then_clone_it - {item.id} in {time_ms(started_on)} ms.")
            if item:
                item.delete()
            if clone:
                clone.delete()

    def test_item_clone_dataset(self):
        self.create_item_then_clone_it(api.models.Dataset)

    def test_item_clone_notebook(self):
        self.create_item_then_clone_it(api.models.Notebook)

    def test_item_clone_recipe(self):
        self.create_item_then_clone_it(api.models.Recipe)

    def test_item_clone_workspace_does_not_work(self):
        url = reverse(f"api:workspace-clone", args=(self.ws1.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
