import io
import os
import os.path
import pytest

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime

import django.utils.http
import django.core.files
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from analitico.utilities import read_json, get_dict_dot

import analitico
import api.models
from .utils import AnaliticoApiTestCase

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets/"


@pytest.mark.django_db
class WebdavTests(AnaliticoApiTestCase):
    def upload_unicorn(self):
        """ The same image is used in a number of tests """
        url = reverse("api:workspace-asset-detail", args=("ws_storage_webdav", "assets", "unicorns-do-it-better.png"))
        response = self.upload_file(url, "unicorns-do-it-better.png", "image/png", token=self.token1)
        self.assertEqual(response.data[0]["id"], "unicorns-do-it-better.png")
        self.assertEqual(response.data[0]["path"], "workspaces/ws_storage_webdav/assets/unicorns-do-it-better.png")
        
        # TODO fix has so it's based on md5 and not modification date
        # self.assertEqual(response.data[0]["hash"], "bb109c5ea3dae456d286c4622b46e2be")
        
        self.assertEqual(
            response.data[0]["url"], "analitico://workspaces/ws_storage_webdav/assets/unicorns-do-it-better.png"
        )
        return url, response

    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:workspace-list")
            self.upload_items(url, analitico.WORKSPACE_PREFIX)

            url = reverse("api:dataset-list")
            self.upload_items(url, analitico.DATASET_PREFIX)

        except Exception as exc:
            print(exc)
            raise exc

    ##
    ## Workspace storage
    ##

    def test_asset_upload(self):
        try:
            url1, _ = self.upload_unicorn()

            url = reverse("api:workspace-detail", args=("ws_storage_webdav",))
            response = self.client.get(url)
            attributes = response.data["attributes"]

            self.assertEqual(len(attributes["assets"]), 1)
            self.assertEqual(attributes["assets"][0]["id"], "unicorns-do-it-better.png")
        except Exception as exc:
            raise exc

    def test_asset_upload_multiple_files(self):
        """ Test multipart encoding to upload multiple files at once """
        try:
            url = reverse("api:workspace-asset-list", args=("ws_storage_webdav", "assets"))

            path1 = os.path.join(ASSETS_PATH, "unicorns-do-it-better.png")
            path2 = os.path.join(ASSETS_PATH, "image_dog2.png")
            path3 = os.path.join(ASSETS_PATH, "image_dog3.webp")

            file1 = open(path1, "rb")
            file2 = open(path2, "rb")
            file3 = open(path3, "rb")

            data = {
                "file1": SimpleUploadedFile("unicorns-do-it-better.png", file1.read(), "image/png"),
                "file2": SimpleUploadedFile("image_dog2.png", file2.read(), "image/png"),
                "file3": SimpleUploadedFile("image_dog3.webp", file3.read(), "image/webp"),
            }

            self.auth_token(self.token1)
            response = self.client.post(url, data, format="multipart")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(len(response.data), 3)

            self.assertEqual(response.data[0]["id"], "unicorns-do-it-better.png")
            self.assertEqual(response.data[1]["id"], "image_dog2.png")
            self.assertEqual(response.data[2]["id"], "image_dog3.webp")

            self.assertEqual(response.data[0]["content_type"], "image/png")
            self.assertEqual(response.data[1]["content_type"], "image/png")
            self.assertEqual(response.data[2]["content_type"], "image/webp")

            self.assertEqual(response.data[0]["size"], os.path.getsize(path1))
            self.assertEqual(response.data[1]["size"], os.path.getsize(path2))
            self.assertEqual(response.data[2]["size"], os.path.getsize(path3))

        except Exception as exc:
            raise exc

    def test_asset_upload_same_file_multiple_times(self):
        """ Test uploading the same file more than once """
        try:
            url1, _ = self.upload_unicorn()
            url2, _ = self.upload_unicorn()
            url3, _ = self.upload_unicorn()

            url = reverse("api:workspace-detail", args=("ws_storage_webdav",))
            response = self.client.get(url)
            attributes = response.data["attributes"]

            # thou shall only have one dog!
            self.assertEqual(len(attributes["assets"]), 1)
            self.assertEqual(attributes["assets"][0]["id"], "unicorns-do-it-better.png")
        except Exception as exc:
            raise exc

    def test_asset_upload_wrong_token_404(self):
        """ Test simple upload of image asset using the wrong token """
        try:
            # asset_id matches filename
            url = reverse(
                "api:workspace-asset-detail", args=("ws_storage_webdav", "assets", "unicorns-do-it-better.png")
            )
            response = self.upload_file(
                url, "unicorns-do-it-better.png", "image/png", self.token2, status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as exc:
            raise exc

    def test_asset_upload_no_token_404(self):
        """ Test simple upload of image asset using no token """
        try:
            # asset_id matches filename
            url = reverse(
                "api:workspace-asset-detail", args=("ws_storage_webdav", "assets", "unicorns-do-it-better.png")
            )
            response = self.upload_file(
                url, "unicorns-do-it-better.png", "image/jpeg", token=None, status_code=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as exc:
            raise exc

    def test_asset_download(self):
        """ Test simple upload and download of image asset """
        try:
            # upload an image to storage
            url = reverse("api:workspace-asset-detail", args=("ws_storage_webdav", "assets", "download1.jpg"))
            response1 = self.upload_file(url, "unicorns-do-it-better.png", "image/jpeg", token=self.token1)
            self.assertEqual(response1.data[0]["id"], "download1.jpg")
            hash = response1.data[0]["hash"]
            etag = f'"{hash}"'

            # now dowload the same asset
            self.auth_token(self.token1)
            response2 = self.client.get(url)
            # we did not indicate caching or etag tags so content should be returned
            self.assertEqual(response2.status_code, status.HTTP_200_OK)
            # we want the server to be streaming contents which is better for large files
            self.assertTrue(isinstance(response2, StreamingHttpResponse))
            # etag is fixed and depends on file contents, not upload time
            self.assertEqual(response2["ETag"], etag)
            self.assertEqual(response2["Content-Type"], "image/jpeg")
        except Exception as exc:
            raise exc

    def test_asset_download_not_found_404(self):
        """ Test simple upload and download with bogus asset_id """
        try:
            # asset was never uploaded
            url = reverse("api:workspace-asset-detail", args=("ws_storage_webdav", "assets", "oh-my-missing-dog.jpg"))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertTrue("oh-my-missing-dog.jpg" in response.data["error"]["title"])
            self.assertEqual(response.data["error"]["status"], "404")
            self.assertEqual(response.data["error"]["code"], "not_found")
        except Exception as exc:
            raise exc

    def OFFtest_asset_download_no_authorization_404(self):
        """ Test upload and download with wrong credentials """
        try:
            url, _ = self.upload_unicorn()

            # dowload the asset with the wrong token
            self.auth_token(self.token2)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.data["error"]["status"], "404")
            self.assertIsNotNone(response.data["error"]["code"])
            self.assertIsNotNone(response.data["error"]["detail"])

            # dowload the same asset with the right token
            self.auth_token(self.token1)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        except Exception as exc:
            raise exc

    def test_asset_download_check_contents(self):
        """ Test upload and download with contents verification """
        try:
            unicorn_path = os.path.join(ASSETS_PATH, "unicorns-do-it-better.png")
            unicorn_content = open(unicorn_path, "rb").read()  
            url, _ = self.upload_unicorn()

            # dowload the same asset and compare data byte by byte
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(isinstance(response, StreamingHttpResponse))

            response_content = b"".join(response.streaming_content)
            self.assertEqual(len(unicorn_content), len(response_content))
            self.assertEqual(unicorn_content, response_content)

        except Exception as exc:
            raise exc

    def test_parse_datetime(self):
        dt1 = django.utils.http.parse_http_date("Sun, 13 Jan 2019 04:07:44 GMT")
        dt2 = django.utils.http.parse_http_date("Sun, 13 Jan 2019 16:07:44 GMT")
        self.assertIsNotNone(dt1)
        self.assertIsNotNone(dt2)
        self.assertLessEqual(dt1, dt2)

        dt1 = django.utils.http.parse_http_date("Sun, 13 Jan 2019 16:07:44 GMT")
        dt2 = django.utils.http.parse_http_date("Sun, 13 Jan 2019 16:07:44 GMT")
        self.assertIsNotNone(dt1)
        self.assertIsNotNone(dt2)
        self.assertEqual(dt1, dt2)

    def test_asset_download_if_none_match(self):
        """ Test downloading an asset with etag specified """
        try:
            # upload an image to storage
            url, response = self.upload_unicorn()
            hash = response.data[0]["hash"]
            etag = f'"{hash}"'

            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match
            headers = {"HTTP_IF_NONE_MATCH": etag}
            response2 = self.client.get(url, **headers)
            # etag matches so asset should not be returned
            self.assertEqual(response2.status_code, status.HTTP_304_NOT_MODIFIED)
            self.assertEqual(response2.content_type, "image/png")
            # TODO etag is fixed and SHOULD depend on file contents, not upload time
            self.assertEqual(response2["ETag"], etag)
        except Exception as exc:
            raise exc

    def test_asset_download_if_none_match_wrong_etag(self):
        """ Test downloading an asset with the wrong etag specified """
        try:
            # upload an image to storage
            url, _ = self.upload_unicorn()

            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match
            headers = {"HTTP_IF_NONE_MATCH": '"WRONGETAG"'}
            response2 = self.client.get(url, **headers)
            # we gave the wrong etag so asset should be returned
            self.assertEqual(response2.status_code, status.HTTP_200_OK)
            self.assertEqual(response2["Content-Type"], "image/png")
            # TODO correct etag should be returned
            # self.assertEqual(response2["ETag"], '"a9f659efd070f3e5b121a54edd8b13d0"')
        except Exception as exc:
            raise exc

    def test_asset_download_if_modified_since(self):
        """ Test downloading an asset with last modification date specified """
        try:
            # upload an image to storage
            url, _ = self.upload_unicorn()

            # plain get with no caching instructions
            response2 = self.client.get(url)
            self.assertIsNotNone(response2["last-modified"])

            # now ask for download but only if newer than our modification date
            headers = {"HTTP_IF_MODIFIED_SINCE": response2["last-modified"]}
            response3 = self.client.get(url, **headers)
            self.assertEqual(response3.status_code, status.HTTP_304_NOT_MODIFIED)
        except Exception as exc:
            raise exc

    def test_asset_download_if_modified_since_earlier(self):
        """ Test downloading an asset while pretending we have an older copy on the client """
        try:
            # upload an image to storage
            url, _ = self.upload_unicorn()

            # plain get with no caching instructions
            response2 = self.client.get(url)
            self.assertIsNotNone(response2["last-modified"])
            last_modified = django.utils.http.parse_http_date(response2["last-modified"])
            last_modified -= 60 * 60  # pretend our copy is 1 hour older

            # ask for download but only if newer than our modification date
            headers = {"HTTP_IF_MODIFIED_SINCE": django.utils.http.http_date(last_modified)}
            response3 = self.client.get(url, **headers)
            self.assertEqual(response3.status_code, status.HTTP_200_OK)
        except Exception as exc:
            raise exc

    def test_asset_download_if_modified_since_later(self):
        """ Test downloading an asset while pretending we have a newer copy on the client """
        try:
            # upload an image to storage
            url, _ = self.upload_unicorn()

            # plain get with no caching instructions
            response2 = self.client.get(url)
            self.assertIsNotNone(response2["last-modified"])
            last_modified = django.utils.http.parse_http_date(response2["last-modified"])
            last_modified += 60 * 60  # pretend our copy is 1 hour newer than the server's

            # ask for download but only if newer than our modification date
            headers = {"HTTP_IF_MODIFIED_SINCE": django.utils.http.http_date(last_modified)}
            response3 = self.client.get(url, **headers)
            self.assertEqual(response3.status_code, status.HTTP_304_NOT_MODIFIED)
        except Exception as exc:
            raise exc

    def test_asset_download_asset_json(self):
        """ Test downloading an asset's details as json """
        try:
            # upload then download json details
            url, _ = self.upload_unicorn()
            url_info = reverse("api:workspace-asset-detail-info", args=("ws_storage_webdav", "assets", "unicorns-do-it-better.png"))
            self.assertEqual(url + "/info", url_info)

            response = self.client.get(url_info)
            self.assertEqual(response["Content-Type"], "application/json")
            self.assertIsNotNone(response.data)

            data = response.data
            self.assertEqual(data["content_type"], "image/png")
            # self.assertEqual(data["etag"], '"a9f659efd070f3e5b121a54edd8b13d0"')
            # self.assertEqual(data["hash"], "a9f659efd070f3e5b121a54edd8b13d0")
            self.assertEqual(data["filename"], "unicorns-do-it-better.png")
            self.assertEqual(data["id"], "unicorns-do-it-better.png")
            self.assertEqual(data["path"], "workspaces/ws_storage_webdav/assets/unicorns-do-it-better.png")
            self.assertEqual(data["url"], "analitico://workspaces/ws_storage_webdav/assets/unicorns-do-it-better.png")
            self.assertEqual(int(data["size"]), 29453)
        except Exception as exc:
            raise exc

    def test_asset_delete(self):
        """ Test uploading then deleting an asset. """
        try:
            url, _ = self.upload_unicorn()

            response1 = self.client.delete(url)
            self.assertEqual(response1.status_code, status.HTTP_204_NO_CONTENT)  # deleted

            response2 = self.client.delete(url)
            self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)  # no longer there
        except Exception as exc:
            raise exc

    def test_asset_delete_no_authorization_404(self):
        """ Test uploading then deleting an asset with the wrong credentials. """
        try:
            url, _ = self.upload_unicorn()

            self.auth_token(self.token2)  # wrong credentials
            response1 = self.client.delete(url)
            self.assertEqual(response1.status_code, status.HTTP_404_NOT_FOUND)  # should not delete

            self.auth_token(self.token1)  # correct credentials
            response2 = self.client.get(url)
            self.assertEqual(response2.status_code, status.HTTP_200_OK)  # asset is still there
        except Exception as exc:
            raise exc
