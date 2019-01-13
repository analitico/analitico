
import io
import os
import os.path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime

import django.utils.http
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

    def _upload_dog(self):
        """ The same dog image is used in a number of tests """
        url = reverse('api:workspace-asset-detail', args=('ws_storage_gcs', 'oh-my-dog.jpg'))
        response = self._upload_file(url, 'image_dog1.jpg', 'image/jpeg')
        self.assertEqual(response.data[0]['id'], 'oh-my-dog.jpg')
        self.assertEqual(response.data[0]['path'], 'workspaces/ws_storage_gcs/assets/oh-my-dog.jpg')
        self.assertEqual(response.data[0]['hash'], 'a9f659efd070f3e5b121a54edd8b13d0')
        return url, response


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
        """ Test basic file storage credentials retrieval and file upload """
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
        """ Uploads a single asset to given url service, performs basic checks """
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
        """ Test simple upload of image asset """
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
        """ Test asset id from URL taking precedence over filename """
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
        """ Test asset id with invalid characters (should not be found) """
        try:
            url = reverse('api:workspace-asset-detail', args=('ws_storage_gcs', 'GOOD')) # won't reverse with invalid chars...
            url = url.replace('GOOD', 'ur$£"l-dOg_2.jpg') # ...replace with invalid chars
            self._upload_file(url, 'image_dog1.jpg', 'image/jpeg', status_code=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            raise exc


    def test_asset_upload_multiple_files(self):
        """ Test multipart encoding to upload multiple files at once """
        try:
            url = reverse('api:workspace-asset-detail', args=('ws_storage_gcs', ''))

            path1 = os.path.join(ASSETS_PATH, 'image_dog1.jpg')
            path2 = os.path.join(ASSETS_PATH, 'image_dog2.png')
            path3 = os.path.join(ASSETS_PATH, 'image_dog3.webp')

            file1 = open(path1, 'rb')
            file2 = open(path2, 'rb')
            file3 = open(path3, 'rb')

            data = {
                'file1': SimpleUploadedFile('image_dog1.jpg', file1.read(), 'image/jpeg'),
                'file2': SimpleUploadedFile('image_dog2.png', file2.read(), 'image/png'),
                'file3': SimpleUploadedFile('image_dog3.webp', file3.read(), 'image/webp')
            }

            self.auth_token(self.token1)
            response = self.client.post(url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(len(response.data), 3)

            self.assertEqual(response.data[0]['id'], 'image_dog1.jpg')
            self.assertEqual(response.data[1]['id'], 'image_dog2.png')
            self.assertEqual(response.data[2]['id'], 'image_dog3.webp')

            self.assertEqual(response.data[0]['content_type'], 'image/jpeg')
            self.assertEqual(response.data[1]['content_type'], 'image/png')
            self.assertEqual(response.data[2]['content_type'], 'image/webp')

            self.assertEqual(response.data[0]['size'], os.path.getsize(path1))
            self.assertEqual(response.data[1]['size'], os.path.getsize(path2))
            self.assertEqual(response.data[2]['size'], os.path.getsize(path3))

        except Exception as exc:
            raise exc


    def test_asset_download(self):
        """ Test simple upload and download of image asset """
        try:
            # upload an image to storage
            url = reverse('api:workspace-asset-detail', args=('ws_storage_gcs', 'download1.jpg'))
            response1 = self._upload_file(url, 'image_dog1.jpg', 'image/jpeg')
            self.assertEqual(response1.data[0]['id'], 'download1.jpg')
            self.assertEqual(response1.data[0]['hash'], 'a9f659efd070f3e5b121a54edd8b13d0')

            # now dowload the same asset
            self.auth_token(self.token1)            
            response2 = self.client.get(url)
            self.assertEqual(response2.status_code, status.HTTP_200_OK) # we did not indicate caching or etag tags so content should be returned
            self.assertTrue(isinstance(response2, StreamingHttpResponse)) # we want the server to be streaming contents which is better for large files
            self.assertEqual(response2['ETag'], '"a9f659efd070f3e5b121a54edd8b13d0"') # etag is fixed and depends on file contents, not upload time
            self.assertEqual(response2['Content-Type'], 'image/jpeg')
        except Exception as exc:
            raise exc


    def test_asset_download_check_contents(self):
        """ Test upload and download with contents verification """
        try:
            dog_path = os.path.join(ASSETS_PATH, 'image_dog1.jpg')
            with open(dog_path, 'rb') as dog_file:
                dog_content = dog_file.read()

            url, _ = self._upload_dog()

            # dowload the same asset and compare data byte by byte
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(isinstance(response, StreamingHttpResponse))

            response_content = b"".join(response.streaming_content)

            self.assertEqual(len(dog_content), len(response_content))
            self.assertEqual(dog_content, response_content)
        except Exception as exc:
            raise exc


    def test_parse_datetime(self):
        dt1 = django.utils.http.parse_http_date('Sun, 13 Jan 2019 04:07:44 GMT')
        dt2 = django.utils.http.parse_http_date('Sun, 13 Jan 2019 16:07:44 GMT')
        self.assertIsNotNone(dt1)
        self.assertIsNotNone(dt2)
        self.assertLessEqual(dt1, dt2)

        dt1 = django.utils.http.parse_http_date('Sun, 13 Jan 2019 16:07:44 GMT')
        dt2 = django.utils.http.parse_http_date('Sun, 13 Jan 2019 16:07:44 GMT')
        self.assertIsNotNone(dt1)
        self.assertIsNotNone(dt2)
        self.assertEqual(dt1, dt2)
 

    def test_asset_download_if_none_match(self):
        """ Test downloading an asset with etag specified """
        try:
            # upload an image to storage
            url, _ = self._upload_dog()

            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match
            headers = {
                'HTTP_IF_NONE_MATCH': '"a9f659efd070f3e5b121a54edd8b13d0"'
            }
            response2 = self.client.get(url, **headers)
            self.assertEqual(response2.status_code, status.HTTP_304_NOT_MODIFIED) # etag matches so asset should not be returned
            self.assertEqual(response2.content_type, 'image/jpeg')
            self.assertEqual(response2['ETag'], '"a9f659efd070f3e5b121a54edd8b13d0"') # etag is fixed and depends on file contents, not upload time
        except Exception as exc:
            raise exc


    def test_asset_download_if_none_match_wrong_etag(self):
        """ Test downloading an asset with the wrong etag specified """
        try:
            # upload an image to storage
            url, _ = self._upload_dog()

            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match
            headers = {
                'HTTP_IF_NONE_MATCH': '"WRONGETAG"'
            }
            response2 = self.client.get(url, **headers)
            self.assertEqual(response2.status_code, status.HTTP_200_OK) # we gave the wrong etag so asset should be returned
            self.assertEqual(response2['Content-Type'], 'image/jpeg')
            self.assertEqual(response2['ETag'], '"a9f659efd070f3e5b121a54edd8b13d0"') # correct etag should be returned
        except Exception as exc:
            raise exc


    def test_asset_download_if_modified_since(self):
        """ Test downloading an asset with last modification date specified """
        try:
            # upload an image to storage
            url, _ = self._upload_dog()

            # plain get with no caching instructions
            response2 = self.client.get(url)
            self.assertIsNotNone(response2['last-modified'])

            # now ask for download but only if newer than our modification date
            headers = {
                'HTTP_IF_MODIFIED_SINCE': response2['last-modified']
            }
            response3 = self.client.get(url, **headers)
            self.assertEqual(response3.status_code, status.HTTP_304_NOT_MODIFIED)
        except Exception as exc:
            raise exc


    def test_asset_download_if_modified_since_earlier(self):
        """ Test downloading an asset while pretending we have an older copy on the client """
        try:
            # upload an image to storage
            url, _ = self._upload_dog()

            # plain get with no caching instructions
            response2 = self.client.get(url)
            self.assertIsNotNone(response2['last-modified'])
            last_modified = django.utils.http.parse_http_date(response2['last-modified'])
            last_modified -= 60 * 60 # pretend our copy is 1 hour older

            headers = {
                # ask for download but only if newer than our modification date
                'HTTP_IF_MODIFIED_SINCE': django.utils.http.http_date(last_modified)
            }
            response3 = self.client.get(url, **headers)
            self.assertEqual(response3.status_code, status.HTTP_200_OK)
        except Exception as exc:
            raise exc


    def test_asset_download_if_modified_since_later(self):
        """ Test downloading an asset while pretending we have a newer copy on the client """
        try:
            # upload an image to storage
            url, _ = self._upload_dog()

            # plain get with no caching instructions
            response2 = self.client.get(url)
            self.assertIsNotNone(response2['last-modified'])
            last_modified = django.utils.http.parse_http_date(response2['last-modified'])
            last_modified += 60 * 60 # pretend our copy is 1 hour newer than the server's

            headers = {
                # ask for download but only if newer than our modification date
                'HTTP_IF_MODIFIED_SINCE': django.utils.http.http_date(last_modified)
            }
            response3 = self.client.get(url, **headers)
            self.assertEqual(response3.status_code, status.HTTP_304_NOT_MODIFIED)
        except Exception as exc:
            raise exc


    def test_asset_download_asset_json(self):
        """ Test downloading an asset's details as json """
        try:
            # upload then download json details
            url, _ = self._upload_dog()
            response = self.client.get(url + '/json')
            self.assertEqual(response['Content-Type'], 'application/json')
            self.assertIsNotNone(response.data)

            data = response.data
            self.assertEqual(data['content_type'], 'image/jpeg')
            self.assertEqual(data['etag'], '"a9f659efd070f3e5b121a54edd8b13d0"')
            self.assertEqual(data['hash'], 'a9f659efd070f3e5b121a54edd8b13d0')
            self.assertEqual(data['filename'], 'image_dog1.jpg')
            self.assertEqual(data['id'], 'oh-my-dog.jpg')
            self.assertEqual(data['path'], 'workspaces/ws_storage_gcs/assets/oh-my-dog.jpg')
            self.assertEqual(data['size'], '49038')
        except Exception as exc:
            raise exc

