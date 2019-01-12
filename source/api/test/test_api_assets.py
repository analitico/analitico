
import os
import os.path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

import django.core.files
from django.core.files.uploadedfile import SimpleUploadedFile

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

    def _upload_file(self, url, asset_name, content_type, token=None, status_code=status.HTTP_201_CREATED):

        asset_path = os.path.join(ASSETS_PATH, asset_name)
        asset_size = os.path.getsize(asset_path)
        with open(asset_path, 'rb') as asset_file:

            asset_data = asset_file.read()
            asset_uploaded = SimpleUploadedFile(asset_name, asset_data, content_type)

            data = {
                'file': asset_uploaded
            }
            self.auth_token(token if token else self.token1)
            response = self.client.post(url, data, format='multipart')
            self.assertEqual(response.status_code, status_code)

            if (status_code == status.HTTP_201_CREATED):
                self.assertEqual(len(response.data), 1)        
                data = response.data[0]
                self.assertEqual(data['content_type'], content_type)
                self.assertEqual(data['filename'], asset_name)
                self.assertEqual(data['size'], asset_size)
            return response


    def test_asset_upload_matching_name(self):
        try:
            url = reverse('api:workspace-asset-detail', args=('ws_storage_gcs', 'image_dog1.jpg')) # asset_id matches filename
            response = self._upload_file(url, 'image_dog1.jpg', 'image/jpeg')
            data = response.data[0]

            self.assertEqual(data['id'], 'image_dog1.jpg')
            self.assertEqual(data['path'], 'workspaces/ws_storage_gcs/assets/image_dog1.jpg')
            self.assertEqual(data['hash'], 'a9f659efd070f3e5b121a54edd8b13d0')
        except Exception as exc:
            raise exc


    def test_asset_upload_with_asset_id(self):
        """ Asset id should take precedence over filename when picking where to store asset """
        try:
            url = reverse('api:workspace-asset-detail', args=('ws_storage_gcs', 'url-dog2.jpg')) # asset_id has priority
            response = self._upload_file(url, 'image_dog1.jpg', 'image/jpeg')
            data = response.data[0]

            self.assertEqual(data['id'], 'url-dog2.jpg')
            self.assertEqual(data['path'], 'workspaces/ws_storage_gcs/assets/url-dog2.jpg')
            self.assertEqual(data['hash'], 'a9f659efd070f3e5b121a54edd8b13d0')
        except Exception as exc:
            raise exc


    def test_asset_upload_with_asset_id_slugified(self):
        """ Asset id with invalid chars should not be found """
        try:
            url = reverse('api:workspace-asset-detail', args=('ws_storage_gcs', 'GOOD')) # won't reverse with invalid chars...
            url = url.replace('GOOD', 'ur$£"l-dOg_2.jpg') # ...replace with invalid chars
            response = self._upload_file(url, 'image_dog1.jpg', 'image/jpeg', status_code=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            raise exc
