import io
import os
import os.path
import pytest

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime

from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.storage.types import (
    ContainerAlreadyExistsError,
    ContainerDoesNotExistError,
    InvalidContainerNameError,
    ObjectError,
)

import django
import django.utils.http
import django.core.files
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from analitico.utilities import read_json, get_dict_dot

import api
import analitico
import api.models
import api.libcloud
from .utils import AnaliticoApiTestCase

import libcloud
import tempfile

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets/"

WEBDAV_URL = "https://u206378-sub4.your-storagebox.de"
WEBDAV_USERNAME = "u206378-sub4"
WEBDAV_PASSWORD = "nGGGWuPsvqcOqzN8"


@pytest.mark.django_db
class WebdavTests(AnaliticoApiTestCase):
    def get_driver(self):
        """ Driver for WebDAV container used by unit testing """
        return api.libcloud.WebdavStorageDriver(WEBDAV_URL, WEBDAV_USERNAME, WEBDAV_PASSWORD)

    def upload_unicorn(self):
        """ The same image is used in a number of tests """
        url = reverse("api:workspace-asset-detail", args=("ws_storage_webdav", "assets", "unicorns-do-it-better.png"))
        response = self.upload_file(url, "unicorns-do-it-better.png", "image/png", token=self.token1)
        self.assertEqual(response.data[0]["id"], "unicorns-do-it-better.png")
        self.assertEqual(response.data[0]["path"], "/workspaces/ws_storage_webdav/assets/unicorns-do-it-better.png")

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
            self.assertIn("hash", response1.data[0])

            # now dowload the same asset
            self.auth_token(self.token1)
            response2 = self.client.get(url)
            # we did not indicate caching or etag tags so content should be returned
            self.assertEqual(response2.status_code, status.HTTP_200_OK)
            # we want the server to be streaming contents which is better for large files
            self.assertTrue(isinstance(response2, StreamingHttpResponse))
            # etag is fixed and depends on file contents, not upload time
            # self.assertEqual(response2["ETag"], "730d-58b84460963e9")
            self.assertEqual(response2["Content-Type"], "image/jpeg")

            # now dowload the same asset
            response3 = self.client.get(url)
            self.assertEqual(response2["ETag"], response3["ETag"])
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

            # pull once to find etag
            response1 = self.client.get(url)
            etag = response1["etag"]

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
            url_info = reverse(
                "api:workspace-asset-detail-info", args=("ws_storage_webdav", "assets", "unicorns-do-it-better.png")
            )
            self.assertEqual(url + "/info", url_info)

            response = self.client.get(url_info)
            self.assertEqual(response["Content-Type"], "application/json")
            self.assertIsNotNone(response.data)

            data = response.data
            self.assertEqual(data["content_type"], "image/png")
            # self.assertEqual(data["etag"], '"730d-58b845739f93b"') # TODO why does etag vary?
            # self.assertEqual(data["hash"], "730d58b8414a9f230")
            self.assertEqual(data["filename"], "unicorns-do-it-better.png")
            self.assertEqual(data["id"], "unicorns-do-it-better.png")
            self.assertEqual(data["path"], "/workspaces/ws_storage_webdav/assets/unicorns-do-it-better.png")
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

    ##
    ## WebDAV driver direct webdav methods
    ##

    def test_webdav_driver_parent_path(self):
        """ Calculating parent of WebDAV path. """
        driver = self.get_driver()

        path = "/prove/workspaces/ws_storage_webdav/assets/unicorns-do-it-better.png"
        self.assertEqual(driver._parent_path(path), "/prove/workspaces/ws_storage_webdav/assets/")
        path = "/prove/workspaces/ws_storage_webdav/assets/"
        self.assertEqual(driver._parent_path(path), "/prove/workspaces/ws_storage_webdav/")
        path = "/prove/"
        self.assertEqual(driver._parent_path(path), "/")
        path = "/"
        self.assertEqual(driver._parent_path(path), None)
        path = None
        self.assertEqual(driver._parent_path(path), None)

    def test_webdav_driver_ls(self):
        """ List contents of a directory. """
        driver = self.get_driver()
        ls = driver.ls("/")

        self.assertGreaterEqual(len(ls), 1)

        container = ls[0]
        self.assertTrue(isinstance(container, libcloud.storage.base.Container))
        self.assertEqual(container.name, "/")

    def test_webdav_driver_mkdir(self):
        """ Make a directory. """
        driver = self.get_driver()

        # directory does not exist yet
        dir_name = "/" + django.utils.crypto.get_random_string() + "/"
        self.assertFalse(driver.exists(dir_name))

        # directory was created?
        driver.mkdir(dir_name)
        self.assertTrue(driver.exists(dir_name))

        # directory was removed?
        driver.rmdir(dir_name)
        self.assertFalse(driver.exists(dir_name))

    def test_webdav_driver_mkdirs(self):
        """ Make and delete a directory with subdirectories. """
        driver = self.get_driver()

        # directory does not exist yet
        dir_name = "/" + django.utils.crypto.get_random_string() + "/sub1/sub2/"
        self.assertFalse(driver.exists(dir_name))

        # mkdir should not work on multiple levels of directory
        with self.assertRaises(api.libcloud.WebdavException):
            driver.mkdir(dir_name)
        self.assertFalse(driver.exists(dir_name))

        # mkdirs works on multiple levels of directory
        driver.mkdirs(dir_name)
        self.assertTrue(driver.exists(dir_name))

        # directory was removed?
        driver.rmdir(dir_name)
        self.assertFalse(driver.exists(dir_name))

    def test_webdav_driver_rmdir_not_empty(self):
        """ Delete a directory that is NOT empty. """
        driver = self.get_driver()

        # create directory
        dir_name = "/" + django.utils.crypto.get_random_string() + "/sub1/sub2/"
        self.assertFalse(driver.exists(dir_name))
        driver.mkdirs(dir_name)
        self.assertTrue(driver.exists(dir_name))

        # write a file in it
        remote_path = os.path.join(dir_name, "pippo.txt")
        data = io.BytesIO(b"This is some stuff")
        driver.upload(data, remote_path)

        # file exists?
        self.assertTrue(driver.exists(remote_path))

        # delete directory that has file in it
        driver.rmdir(dir_name)
        self.assertFalse(driver.exists(dir_name))
        self.assertFalse(driver.exists(remote_path))

    def test_webdav_driver_cdn(self):
        """ CDN methods are not implemented. """
        driver = self.get_driver()
        with self.assertRaises(NotImplementedError):
            driver.get_container_cdn_url(None)
        with self.assertRaises(NotImplementedError):
            driver.get_object_cdn_url(None)
        with self.assertRaises(NotImplementedError):
            driver.enable_container_cdn(None)
        with self.assertRaises(NotImplementedError):
            driver.enable_object_cdn(None)

    def test_webdav_driver_download(self):
        """ Create a file, download to file-obj, download to filename, check. """
        driver = self.get_driver()

        dir_name = "/" + django.utils.crypto.get_random_string() + "/sub1/sub2/"
        remote_path = dir_name + "file.txt"
        file_data = b"This is some stuff"

        # create file
        driver.mkdirs(dir_name)
        driver.upload(io.BytesIO(file_data), remote_path)
        self.assertTrue(driver.exists(remote_path))

        # download file as a stream, check contents
        remote_data = next(iter(driver.download_as_stream(remote_path)))
        self.assertEqual(file_data, remote_data)

        with tempfile.NamedTemporaryFile() as f:
            # download to file object
            driver.download(remote_path, f.file)
            f.file.seek(0)
            remote_data = f.file.read()
            self.assertEqual(file_data, remote_data)

        with tempfile.NamedTemporaryFile() as f:
            # download to file name
            driver.download(remote_path, f.name)
            f.file.seek(0)
            remote_data = f.file.read()
            self.assertEqual(file_data, remote_data)

        driver.rmdir(dir_name)

    ##
    ## StorageDriver methods
    ##

    CONTAINER_NAMES = ["Mickey Mouse", "Donald Duck", "Goofy", "Clarabelle", "Daisy Duck", "Scrooge McDuck"]

    def test_webdav_driver_create_container(self):
        driver = self.get_driver()

        # new container does not exist
        container_name = "/" + django.utils.crypto.get_random_string() + "/sub1/sub2/"
        with self.assertRaises(ContainerDoesNotExistError):
            driver.get_container(container_name)

        # create and check
        container = driver.create_container(container_name)
        self.assertIsInstance(container, Container)
        self.assertEqual(container.name, container_name)

        # get and check
        container = driver.get_container(container_name)
        self.assertIsInstance(container, Container)
        self.assertEqual(container.name, container_name)

        # delete and check
        driver.delete_container(container)
        with self.assertRaises(ContainerDoesNotExistError):
            driver.get_container(container_name)

    def test_webdav_driver_iterate_containers(self):
        driver = self.get_driver()
        container_name = "/" + django.utils.crypto.get_random_string() + "/"
        try:
            for name in self.CONTAINER_NAMES:
                subcontainer_name = os.path.join(container_name, name) + "/"

                subcontainer = driver.create_container(subcontainer_name)
                self.assertEqual(subcontainer.name, subcontainer_name)
                subcontainer = driver.get_container(subcontainer_name)
                self.assertEqual(subcontainer.name, subcontainer_name)

            # iterate top level containers (there should be a few but at the very least one)
            container = next(item for item in driver.iterate_containers() if item.name == container_name)
            self.assertIsNotNone(container)

        finally:
            driver.rmdir(container_name)

    def test_webdav_driver_iterate_container_objects(self):
        driver = self.get_driver()
        try:
            container_name = "/" + django.utils.crypto.get_random_string() + "/"

            # create a number of directories
            for name in self.CONTAINER_NAMES:
                subcontainer_name = os.path.join(container_name, name) + "/"
                subcontainer = driver.create_container(subcontainer_name)
                self.assertEqual(subcontainer.name, subcontainer_name)
                subcontainer = driver.get_container(subcontainer_name)
                self.assertEqual(subcontainer.name, subcontainer_name)

            # containers are listed by ls()
            items = driver.ls(container_name)
            self.assertEqual(len(items), len(self.CONTAINER_NAMES) + 1)

            # containers are NOT listed by storage APIs
            parent_container = driver.get_container(container_name)
            items = list(driver.iterate_container_objects(parent_container))
            self.assertEqual(len(items), 0)

            # now upload a few text files
            for name in self.CONTAINER_NAMES:
                driver.upload_object_via_stream(io.BytesIO(b"This is it"), parent_container, name + ".txt")

            # containers + object are listed by ls()
            items = driver.ls(container_name)
            self.assertEqual(len(items), (2 * len(self.CONTAINER_NAMES)) + 1)

            # now the list should contain the text files
            items = list(driver.iterate_container_objects(parent_container))
            self.assertEqual(len(items), len(self.CONTAINER_NAMES))

        finally:
            driver.rmdir(container_name)

    def test_webdav_driver_get_container(self):
        """ Create a container with nested folders then retrieve them individually. """
        driver = self.get_driver()
        try:
            base_name = "/" + django.utils.crypto.get_random_string() + "/"
            container_name = base_name + "abc/def/ghi/"
            container = driver.create_container(container_name)
            self.assertEqual(container.name, container_name)

            obj_data = b"This is it"
            obj_name = "test.txt"
            obj = driver.upload_object_via_stream(io.BytesIO(obj_data), container, obj_name)
            self.assertIsInstance(obj, Object)
            self.assertEqual(obj.name, container_name + obj_name)

            container1_name = base_name + "abc/"
            container1 = driver.get_container(container1_name)
            self.assertIsInstance(container1, Container)
            self.assertEqual(container1.name, container1_name)

            container2_name = base_name + "abc/def/"
            container2 = driver.get_container(container2_name)
            self.assertIsInstance(container2, Container)
            self.assertEqual(container2.name, container2_name)

            container3_name = base_name + "abc/def/ghi/"
            container3 = driver.get_container(container3_name)
            self.assertIsInstance(container3, Container)
            self.assertEqual(container3.name, container3_name)

        finally:
            driver.rmdir(container_name)


    def test_webdav_driver_upload_get_download_object(self):
        driver = self.get_driver()
        try:
            base_name = "/" + django.utils.crypto.get_random_string() + "/"
            container_name = base_name + "abc/def/ghi/"
            container = driver.create_container(container_name)
            self.assertEqual(container.name, container_name)

            obj_data = b"This is it"
            obj_name = "test.txt"
            obj = driver.upload_object_via_stream(io.BytesIO(obj_data), container, obj_name)
            self.assertIsInstance(obj, Object)
            self.assertEqual(obj.name, container_name + obj_name)

            # get and download object
            obj = driver.get_object(container_name, obj_name)
            self.assertIsInstance(obj, Object)
            self.assertEqual(obj.name, container_name + obj_name)
            self.assertEqual(obj.container.name, container_name)

            # can't overwrite unless specified
            with tempfile.NamedTemporaryFile() as f:
                with self.assertRaises(libcloud.common.types.LibcloudError):
                    driver.download_object(obj, f.name)

            # download and overwrite
            with tempfile.NamedTemporaryFile() as f:
                driver.download_object(obj, f.name, overwrite_existing=True)
                downloaded_data = f.file.read()
                self.assertEqual(obj_data, downloaded_data)
            
            # streaming download
            downloaded_data = next(iter(driver.download_object_as_stream(obj)))
            self.assertEqual(obj_data, downloaded_data)

        finally:
            driver.rmdir(container_name)
