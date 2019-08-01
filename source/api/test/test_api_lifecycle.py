import tempfile
import pytest

from pathlib import Path
from django.test import tag
from django.urls import reverse
from rest_framework import status

import analitico

from analitico import logger
from .utils import AnaliticoApiTestCase
from api.models import Dataset, Recipe, Notebook, Model, Workspace

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member
# pylint: disable=unused-variable

@pytest.mark.django_db
class LifecycleTests(AnaliticoApiTestCase):
    """ Test life cycle operations like provisioning and deprovisioning storage, etc """

    def setUp(self):
        self.setup_basics()

    def create_item_file_then_delete_item_verify_file_deletion(self, item):
        try:
            # upload file to dataset storage
            url, _ = self.upload_unicorn(item)  # eg: /api/datasets/ds_xxx/files/unicorn.jpg
            remote_path = item.storage_base_path + "unicorns-do-it-better.png"
            driver = item.storage.driver

            with tempfile.NamedTemporaryFile(suffix=Path(remote_path).suffix) as f:
                # download unicorn to local file
                driver.download(remote_path, f.name)

                # deleting item will delete files as well
                item.delete()
                item = None

                # download unicorn and make sure it's no longer there
                with self.assertRaises(Exception):
                    driver.download(remote_path, f.name)
        except Exception as exc:
            logger.error(exc)

        finally:
            if item:
                item.delete()

    def test_lifecycle_delete_dataset_storage(self):
        item = Dataset(workspace=self.ws1)
        item.save()
        self.create_item_file_then_delete_item_verify_file_deletion(item)

    def test_lifecycle_delete_recipe_storage(self):
        item = Recipe(workspace=self.ws1)
        item.save()
        self.create_item_file_then_delete_item_verify_file_deletion(item)

    def test_lifecycle_delete_notebook_storage(self):
        item = Notebook(workspace=self.ws1)
        item.save()
        self.create_item_file_then_delete_item_verify_file_deletion(item)

    def test_lifecycle_delete_model_storage(self):
        item = Model(workspace=self.ws1)
        item.save()
        self.create_item_file_then_delete_item_verify_file_deletion(item)

    def test_lifecycle_delete_workspace_storage(self):
        # TODO we should have a test where we provision a new workspace with its own storage account then delete it
        pass
