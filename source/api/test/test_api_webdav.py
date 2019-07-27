import io
import os
import os.path
import pytest

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime
from django.core.files.uploadedfile import SimpleUploadedFile

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
from analitico.utilities import read_json, get_dict_dot, read_text

import api
import analitico
import api.models
import api.libcloud
from .utils import AnaliticoApiTestCase, NOTEBOOKS_PATH

import libcloud
import tempfile

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets/"
UNICORN_FILENAME = "unicorns-do-it-better.png"

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
        url = reverse("api:workspace-files", args=("ws_storage_webdav", UNICORN_FILENAME))
        response = self.upload_file(url, UNICORN_FILENAME, "image/png", token=self.token1)
        return url, response

    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:workspace-list")
            self.upload_items(url, analitico.WORKSPACE_PREFIX)

            url = reverse("api:dataset-list")
            self.upload_items(url, analitico.DATASET_PREFIX)

            # specific workspace that has webdav storage backing
            self.ws_storage_webdav = api.models.Workspace.objects.get(pk="ws_storage_webdav")

        except Exception as exc:
            print(exc)
            raise exc

    ##
    ## Workspace storage
    ##

    # multiple uploads are not supported for now
    def OFFtest_asset_upload_multiple_files(self):
        """ Test multipart encoding to upload multiple files at once """
        try:
            url = reverse("api:workspace-files", args=("ws_storage_webdav",))

            path1 = os.path.join(ASSETS_PATH, UNICORN_FILENAME)
            path2 = os.path.join(ASSETS_PATH, "image_dog2.png")
            path3 = os.path.join(ASSETS_PATH, "image_dog3.webp")

            file1 = open(path1, "rb")
            file2 = open(path2, "rb")
            file3 = open(path3, "rb")

            data = {
                "file1": SimpleUploadedFile(UNICORN_FILENAME, file1.read(), "image/png"),
                "file2": SimpleUploadedFile("image_dog2.png", file2.read(), "image/png"),
                "file3": SimpleUploadedFile("image_dog3.webp", file3.read(), "image/webp"),
            }

            self.auth_token(self.token1)
            response = self.client.post(url, data, format="multipart")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(len(response.data), 3)

            self.assertEqual(response.data[0]["id"], UNICORN_FILENAME)
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

    def test_asset_upload_wrong_token_404(self):
        """ Test simple upload of image asset using the wrong token """
        try:
            # asset_id matches filename
            url = reverse("api:workspace-files", args=("ws_storage_webdav", UNICORN_FILENAME))
            self.upload_file(url, UNICORN_FILENAME, "image/png", self.token2, status_code=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            raise exc

    def test_asset_upload_no_token_404(self):
        """ Test simple upload of image asset using no token """
        try:
            # asset_id matches filename
            url = reverse("api:workspace-files", args=("ws_storage_webdav", UNICORN_FILENAME))
            self.upload_file(url, UNICORN_FILENAME, "image/jpeg", token=None, status_code=status.HTTP_401_UNAUTHORIZED)
        except Exception as exc:
            raise exc

    def test_asset_download(self):
        """ Test simple upload and download of image asset """
        try:
            # upload an image to storage
            url = reverse("api:workspace-files", args=("ws_storage_webdav", "download1.jpg"))
            self.upload_file(url, UNICORN_FILENAME, "image/jpeg", token=self.token1)

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
            url = reverse("api:workspace-files", args=("ws_storage_webdav", "oh-my-missing-dog.jpg"))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertTrue("oh-my-missing-dog.jpg" in response.data["error"]["title"])
            self.assertEqual(response.data["error"]["status"], "404")
            self.assertEqual(response.data["error"]["code"], "error")
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
            unicorn_path = os.path.join(ASSETS_PATH, UNICORN_FILENAME)
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
            url, _ = self.upload_unicorn()

            # pull once to find etag
            response1 = self.client.get(url)
            etag = response1["etag"]

            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match
            headers = {"HTTP_IF_NONE_MATCH": etag}
            response2 = self.client.get(url, **headers)
            # etag matches so asset should not be returned
            self.assertEqual(response2.status_code, status.HTTP_304_NOT_MODIFIED)
            # self.assertEqual(response2.content_type, "image/png")
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

    def test_asset_delete(self):
        """ Test uploading then deleting an asset. """
        try:
            url, _ = self.upload_unicorn()

            response1 = self.client.delete(url)
            self.assertEqual(response1.status_code, status.HTTP_204_NO_CONTENT)  # deleted

            response2 = self.client.delete(url)

            # TODO webdav / handle delete when file does not exists #323
            # self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)  # no longer there
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

    def get_random_path(self):
        return "/tst_" + django.utils.crypto.get_random_string().lower()

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

    def test_webdav_driver_move(self):
        """ Upload a file then change its name. """
        driver = self.get_driver()

        path1 = self.get_random_path() + ".txt"
        path2 = self.get_random_path() + ".txt"

        # create file in first location
        driver.upload(io.BytesIO(b"Tell me something new"), path1)
        self.assertTrue(driver.exists(path1))
        self.assertFalse(driver.exists(path2))

        # rename path1 to path2
        driver.move(path1, path2)
        self.assertFalse(driver.exists(path1))
        self.assertTrue(driver.exists(path2))

        # put original name back
        driver.move(path2, path1)
        self.assertTrue(driver.exists(path1))
        self.assertFalse(driver.exists(path2))

        driver.delete(path1)

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

    def test_webdav_driver_upload_with_extra(self):
        driver = self.get_driver()
        try:
            obj_name = "tst_" + django.utils.crypto.get_random_string() + ".txt"
            obj_data = b"This is it "
            obj_extra = {
                "property1": "value1",
                "property2": 2,
                "raN-Dom_STuff": django.utils.crypto.get_random_string(),
                "    extra-spaces": "No!",
            }

            # upload with "extra" metadata
            container = driver.create_container("/")
            obj = driver.upload_object_via_stream(io.BytesIO(obj_data), container, obj_name, extra=obj_extra)
            self.assertIsInstance(obj, Object)
            self.assertEqual(obj.meta_data["property1"], "value1")
            self.assertEqual(obj.meta_data["property2"], "2")
            self.assertEqual(obj.meta_data["ran-dom_stuff"], obj_extra["raN-Dom_STuff"])
            self.assertEqual(obj.meta_data["extra-spaces"], "No!")

            # change/replace extra
            driver.set_metadata("/" + obj_name, metadata={"extra1": "value1"})
            obj = driver.get_object(container.name, obj_name)
            self.assertEqual(len(obj.meta_data), 1)
            self.assertEqual(obj.meta_data["extra1"], "value1")

            # remove all
            driver.set_metadata("/" + obj_name, metadata=None)
            obj = driver.get_object(container.name, obj_name)
            self.assertFalse(obj.meta_data)

        finally:
            driver.delete("/" + obj_name)

    ##
    ## /api/workspaces/ws_xxx/files/ methods
    ##

    def test_webdav_files_api_list_file(self):
        driver = self.get_driver()
        try:
            obj_name = "tst_" + django.utils.crypto.get_random_string() + ".txt"
            obj_data = b"This is it "
            obj_extra = {"property1": "value1", "property2": 2}

            # upload with metadata
            container = driver.create_container("/")
            obj = driver.upload_object_via_stream(io.BytesIO(obj_data), container, obj_name, extra=obj_extra)

            # retrieve file via /files/url api
            url = reverse("api:workspace-files", args=("ws_storage_webdav", obj_name)) + "?metadata=true"
            response = self.client.get(url)
            data = response.data
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["type"], "analitico/file")
            self.assertEqual(data[0]["id"], "/" + obj_name)
            self.assertEqual(data[0]["id"], obj.name)
            self.assertEqual(data[0]["attributes"]["content_type"], "text/plain")
            self.assertEqual(data[0]["attributes"]["size"], 11)
            self.assertEqual(data[0]["attributes"]["metadata"]["property1"], "value1")
            self.assertEqual(data[0]["attributes"]["metadata"]["property2"], "2")

            # retrieve entire directory via /files api
            url = reverse("api:workspace-files", args=("ws_storage_webdav", "")) + "?metadata=true"
            response = self.client.get(url)
            data = response.data
            self.assertGreater(len(data), 1)
            self.assertEqual(data[0]["type"], "analitico/directory")
            self.assertEqual(data[0]["id"], "/")

        finally:
            driver.delete("/" + obj_name)

    def test_webdav_files_api_put_get_file_contents(self):
        """ Upload raw files directly via /files api """
        driver = self.get_driver()
        try:
            obj_name = "tst_" + django.utils.crypto.get_random_string() + ".txt"
            obj_data = b"This is it"

            # TODO save extras as well
            obj_extra = {"property1": "value1", "property2": 2}

            # upload file contents via /webdav api
            url = reverse("api:workspace-files", args=("ws_storage_webdav", obj_name))  # raw file url
            response = self.client.put(url, data=obj_data)
            self.assertEqual(response.status_code, 204)

            # retrieve info directly from driver
            ls0 = driver.ls(obj_name)[0]

            # retrieve contents from raw file api
            # make sure we do streaming downloads
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.streaming)
            data = b"".join(response.streaming_content)
            self.assertEqual(data, obj_data)
            self.assertEqual(response["ETag"], ls0.extra["etag"])
            self.assertEqual(response["Last-Modified"], ls0.extra["last_modified"])
            self.assertEqual(int(response["Content-Length"]), ls0.size)
            self.assertEqual(int(response["Content-Length"]), len(data))

            # delete item
            response = self.client.delete(url)
            self.assertEqual(response.status_code, 204)
            obj_name = None

            # retrieve item which no longer exists
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

        finally:
            if obj_name:
                driver.delete("/" + obj_name)

    def test_webdav_files_api_move_in_workspace(self):
        """ Move a file via /files api """
        driver = self.get_driver()
        try:
            path1 = self.get_random_path() + ".txt"
            path2 = self.get_random_path() + ".txt"

            url1 = reverse("api:workspace-files", args=("ws_storage_webdav", path1[1:]))
            url2 = reverse("api:workspace-files", args=("ws_storage_webdav", path2[1:]))

            # create file in first location
            driver.upload(io.BytesIO(b"Tell me something new"), path1)
            self.assertTrue(driver.exists(path1))
            self.assertFalse(driver.exists(path2))

            # retrieve item information
            response1 = self.client.get(url1 + "?metadata=true")
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
            data1 = response1.data[0]

            # change name and update (rename)
            data1["id"] = path2
            response2 = self.client.put(url1 + "?metadata=true", data=data1)
            self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

            # check if file actually moved
            self.assertFalse(driver.exists(path1))
            self.assertTrue(driver.exists(path2))

            # download item data (not the metadata)
            response3 = self.client.get(url2)
            self.assertEqual(response3.status_code, status.HTTP_200_OK)
            data3 = b"".join(response3.streaming_content)
            self.assertEqual(data3, b"Tell me something new")

        finally:
            driver.delete(path2)

    def test_webdav_files_api_move_in_notebook(self):
        """ Move a file via /files api """
        driver = self.get_driver()
        try:
            item = api.models.Notebook(workspace=self.ws_storage_webdav)
            item.save()

            contents = ("Tell me something new: " + django.utils.crypto.get_random_string().lower()).encode()
            base_path = f"{item.type}s/{item.id}"
            path1 = self.get_random_path() + ".txt"
            path2 = self.get_random_path() + ".txt"

            url1 = reverse("api:notebook-files", args=(item.id, path1[1:]))
            url2 = reverse("api:notebook-files", args=(item.id, path2[1:]))

            # create file in first location
            driver.mkdirs(base_path)
            driver.upload(io.BytesIO(contents), base_path + path1)
            self.assertTrue(driver.exists(base_path + path1))
            self.assertFalse(driver.exists(base_path + path2))

            # retrieve item contents
            response3 = self.client.get(url1)
            self.assertEqual(response3.status_code, status.HTTP_200_OK)
            data3 = b"".join(response3.streaming_content)
            self.assertEqual(data3, contents)

            # retrieve item information
            response1 = self.client.get(url1 + "?metadata=true")
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
            data1 = response1.data[0]

            # change name and update (rename)
            data1["id"] = path2
            response2 = self.client.put(url1 + "?metadata=true", data=data1)
            self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

            # check if file actually moved
            self.assertFalse(driver.exists(base_path + path1))
            self.assertTrue(driver.exists(base_path + path2))

            # download item data (not the metadata)
            response3 = self.client.get(url2)
            self.assertEqual(response3.status_code, status.HTTP_200_OK)
            data3 = b"".join(response3.streaming_content)
            self.assertEqual(data3, contents)

        finally:
            driver.delete(base_path + path2)

    def test_webdav_files_api_get_metadataheaders(self):
        """ Move a file via /files api """
        driver = self.get_driver()
        try:
            # create file with metadata
            metadata = {"key1": "value1", "key2": "value2", "key with space": 8, "dash-me": "yeah"}
            path = self.get_random_path() + ".txt"
            url = reverse("api:workspace-files", args=("ws_storage_webdav", path[1:]))

            # TODO add support for unicode chars #223
            # extra = {"meta_data": {"key1": "value1", "key2": "value2", "key with space": 8, "dash-me": "yeah", "unicode chars": "ÿëéàaa" }}

            # create file with metadata
            driver.upload(io.BytesIO(b"Tell me something new"), path, metadata=metadata)

            # retrieve item, check metadata headers
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertEqual(response["x-amz-meta-key1"], "value1")
            self.assertEqual(response["x-amz-meta-key2"], "value2")
            self.assertEqual(response["x-amz-meta-key-with-space"], "8")
            self.assertEqual(response["x-amz-meta-dash-me"], "yeah")

        finally:
            driver.delete(path)

    def do_webdav_files_api_put_get_file_contents_on_custom_route(self, base_url):
        """ Upload raw files directly via /recipes/rx_xxx/files api """
        try:
            # try item in main dir, sub and sub sub
            for prefix in ("", "sub/", "sub1/sub2/"):
                obj_name = prefix + "tst_" + django.utils.crypto.get_random_string() + ".txt"
                obj_data = b"This is it"

                # upload file contents via /webdav api
                url = base_url + obj_name
                response = self.client.put(url, data=obj_data)
                self.assertEqual(response.status_code, 204)

                # retrieve metadata contents from file api
                response = self.client.get(url + "?metadata=true")
                self.assertEqual(response.status_code, 200)
                item = response.data[0]
                self.assertEqual(item["id"], "/" + obj_name)

                # retrieve contents from raw file api
                # make sure we do streaming downloads
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.streaming)
                data = b"".join(response.streaming_content)
                self.assertEqual(data, obj_data)
                self.assertEqual(response["ETag"], item["attributes"]["etag"])
                self.assertEqual(response["Last-Modified"], item["attributes"]["last_modified"])
                self.assertEqual(int(response["Content-Length"]), int(item["attributes"]["size"]))
                self.assertEqual(int(response["Content-Length"]), len(data))

                # delete item
                response = self.client.delete(url)
                self.assertEqual(response.status_code, 204)
                obj_name = None

                # retrieve item which no longer exists
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

        finally:
            if obj_name:
                response = self.client.delete(url)

    def test_webdav_files_api_put_get_file_contents_recipes_route(self):
        """ Test /files route on Recipe models """
        try:
            item = api.models.Recipe(workspace=self.ws_storage_webdav)
            item.save()
            base_url = reverse("api:recipe-files", args=(item.id, ""))
            self.do_webdav_files_api_put_get_file_contents_on_custom_route(base_url)
        finally:
            item.delete()
            item.save()

    def test_webdav_files_api_put_get_file_contents_datasets_route(self):
        """ Test /files route on Dataset models """
        try:
            item = api.models.Dataset(workspace=self.ws_storage_webdav)
            item.save()
            base_url = reverse("api:dataset-files", args=(item.id, ""))
            self.do_webdav_files_api_put_get_file_contents_on_custom_route(base_url)
        finally:
            item.delete()
            item.save()

    def test_webdav_files_api_put_get_file_contents_notebooks_route(self):
        """ Test /files route on Notebooks models """
        try:
            item = api.models.Notebook(workspace=self.ws_storage_webdav)
            item.save()
            base_url = reverse("api:notebook-files", args=(item.id, ""))
            self.do_webdav_files_api_put_get_file_contents_on_custom_route(base_url)
        finally:
            item.delete()
            item.save()

    def do_webdav_files_api_put_as_form_get_file_contents_on_custom_route(self, base_url):
        """ Upload form encoded files directly via /recipes/rx_xxx/files api """
        try:
            # try item in main dir, sub and sub sub
            for prefix in ("", "sub/", "sub1/sub2/"):
                obj_name = prefix + "tst_" + django.utils.crypto.get_random_string() + ".ipynb"
                obj_path = os.path.join(NOTEBOOKS_PATH, "notebook01.ipynb")

                with open(obj_path, "rb") as fp:
                    obj_data = fp.read()
                    obj_uploaded = SimpleUploadedFile("notebook.ipynb", obj_data)

                    # upload file contents via /webdav api
                    url = base_url + obj_name
                    response = self.client.put(url, {"file": obj_uploaded}, format="multipart")
                    self.assertEqual(response.status_code, 204)

                # retrieve metadata contents from file api
                response = self.client.get(url + "?metadata=true")
                self.assertEqual(response.status_code, 200)
                item = response.data[0]
                self.assertEqual(item["id"], "/" + obj_name)

                # retrieve contents from raw file api
                # make sure we do streaming downloads
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.streaming)
                data = b"".join(response.streaming_content)
                self.assertEqual(data, obj_data)
                self.assertEqual(response["ETag"], item["attributes"]["etag"])
                self.assertEqual(response["Last-Modified"], item["attributes"]["last_modified"])
                self.assertEqual(int(response["Content-Length"]), int(item["attributes"]["size"]))
                self.assertEqual(int(response["Content-Length"]), len(data))

                # delete item
                response = self.client.delete(url)
                self.assertEqual(response.status_code, 204)
                obj_name = None

                # retrieve item which no longer exists
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

        finally:
            if obj_name:
                response = self.client.delete(url)

    def test_webdav_files_api_put_as_form_get_file_contents_notebooks_route(self):
        """ Test /files route on Notebooks models using form upload """
        try:
            item = api.models.Notebook(workspace=self.ws_storage_webdav)
            item.save()
            base_url = reverse("api:notebook-files", args=(item.id, ""))
            self.do_webdav_files_api_put_as_form_get_file_contents_on_custom_route(base_url)
        finally:
            item.delete()
            item.save()
