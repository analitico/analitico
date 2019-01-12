
import os

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from analitico.utilities import read_json, get_dict_dot

import api.models
import api.test

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + '/assets/'

class AssetsTests(api.test.APITestCase):

    def setUp(self):
        self.setup_basics()
        try: 
            url = reverse('api:workspace-list')
            self.upload_items(url, api.models.WORKSPACE_PREFIX)

            url = reverse('api:dataset-list')
            self.upload_items(url, api.models.DATASET_PREFIX)

        except Exception as exc:
            print(exc)
            raise exc


    ##
    ## Workspace storage
    ##

    def test_workspace_storage(self):
        try:
            import api.storage
            import datetime
            import tempfile

            storage = api.storage.Storage.factory(None)
            with tempfile.NamedTemporaryFile("w") as tmp1:
                txt1 = 'Testing cloud storage on ' + datetime.datetime.now().isoformat()
                tmp1.write(txt1)
                tmp1.seek(0)

                obj = storage.driver.upload_object(tmp1.name, storage.container, 'test/testing.txt')
                with tempfile.NamedTemporaryFile("w") as tmp2:
                    storage.driver.download_object(obj, tmp2.name, overwrite_existing=True)
                    with open(tmp2.name, "r") as tmp2r:
                        txt2 = tmp2r.read()
                        self.assertEqual(txt1, txt2)
        except Exception as exc:
            raise exc


    def test_workspace_storage_gcs2(self):
        item = self.get_item('workspace', 'ws_storage_gcs', token=self.token1)


    ##
    ## Assets
    ##

    def test_asset_upload(self):
        try:
            self.auth_token(self.token1)

            # detail=True
            #url = reverse('api:workspace-pippo', args=('ws_storage_gcs',))

            url = reverse('api:workspace-asset-detail', args=('ws_storage_gcs', 'reverse-dog1.jpg'))

            #url = reverse('api:workspace-pippo')
            #url = reverse('api:workspace-azione', args=('ws_storage_gcs',))
            #url = reverse('api:workspace-detail', args=('ws_storage_gcs',))

            image_path = os.path.join(ASSETS_PATH, 'image_dog1.jpg')
            with open(image_path) as image_file:
                response = self.client.post(url, { 'name': 'dog1.jpg', 'attachment': image_file }, content_type='image/jpg')
#                response = self.client.post(url, { 'name': 'dog1.jpg', 'attachment': image_file })
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        except Exception as exc:
            raise exc
