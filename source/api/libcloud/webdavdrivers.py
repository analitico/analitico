""" Storage driver for WebDAV network filesystem in Apache libcloud. """

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement

import os
import re
import unicodedata
import simplejson as json

from pathlib import Path
from libcloud.utils.py3 import u
from libcloud.common.base import Connection
from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.common.types import LibcloudError
from libcloud.storage.types import (
    ContainerAlreadyExistsError,
    ContainerDoesNotExistError,
    InvalidContainerNameError,
    ObjectError,
)

import urllib
import requests
import xml.etree.cElementTree as xml
from xml.sax.saxutils import escape
from collections import OrderedDict
import logging

from numbers import Number
from http.client import responses as HTTP_CODES
from urllib.parse import urlparse

logger = logging.getLogger("webdav")

DOWNLOAD_CHUNK_SIZE_BYTES = 1 * 1024 * 1024

# tag used in extra for object metadata.
# we use meta_data to be compatible with s3.
METADATA_EXTRA_TAG = "meta_data"

# WebDAV methods based on code from easywebdav updated/fixed for python3/libcloud:
# Copyright (c) 2012, Amnon Grossman
# https://raw.githubusercontent.com/amnong/easywebdav/master/easywebdav/client.py


def codestr(code):
    return HTTP_CODES.get(code, "UNKNOWN")


def xml_prop(elem, name, default=None):
    child = elem.find(".//{DAV:}" + name)
    return default if child is None else child.text


def xml_extra_prop(elem, name, default=None):
    child = elem.find(".//{analitico}" + name)
    return default if child is None else child.text


def prop(elem, name, default=None):
    child = elem.find(".//{DAV:}" + name)
    return default if child is None else child.text


def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def metadata_to_amz_meta_headers(metadata: dict) -> dict:
    """ 
    Returns obj.meta_data converted to a dictionary of key/value headers that
    we can use to return the object's metadata as http headers in a way that 
    is compatible with how it's done on Amazon S3.
    https://docs.aws.amazon.com/AmazonS3/latest/dev/UsingMetadata.html
    """
    headers = OrderedDict()
    if metadata:
        skipped = 0
        for key, value in metadata.items():
            try:
                ascii_value = value.encode("ascii", "replace")
            except Exception:
                skipped += 1
            headers["x-amz-meta-" + slugify(key)] = ascii_value
            if skipped > 0:
                # implement x-amz-missing-meta for unencodable headers #223
                headers["x-amz-missing-meta"] = str(skipped)
    return headers


class WebdavException(LibcloudError):
    """ WebdavException shows method, expected status codes and actual status code reported by server. """

    _OPERATIONS = dict(
        HEAD="get header",
        GET="download",
        PUT="upload",
        DELETE="delete",
        MKCOL="create directory",
        PROPFIND="list directory",
        MOVE="rename",
    )

    def __init__(self, method, path, expected_code, actual_code):
        self.method = method
        self.path = path
        self.expected_code = expected_code
        self.actual_code = actual_code
        operation_name = self._OPERATIONS[method]
        self.reason = f'Failed to {operation_name} "{path}"'
        expected_codes = (expected_code,) if isinstance(expected_code, Number) else expected_code
        expected_codes_str = ", ".join("{0} {1}".format(code, codestr(code)) for code in expected_codes)
        actual_code_str = codestr(actual_code)
        msg = f"{self.reason}.\noperation:  {method} {path}\nexpected: {expected_codes_str}, actual: {actual_code} {actual_code_str}"
        super(WebdavException, self).__init__(msg)


class WebdavStorageDriver(StorageDriver):
    """ Apache libcloud storage driver for WebDAV shares. """

    connectionCls = Connection
    name = "WebDAV"
    website = "https://analitico.ai"
    hash_type = "md5"

    # server base url
    url = None

    def __init__(self, url, username=None, password=None, auth=None, verify_ssl=True, certificate=None):
        assert url and not url.endswith("/"), "WebDAV server url should not end with slash"

        self.url = url
        self.cwd = "/"

        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.stream = True

        if certificate:
            self.session.cert = certificate
        if auth:
            self.session.auth = auth
        elif username and password:
            self.session.auth = (username, password)

    ##
    ## WebDAV direct access extensions
    ##

    def _normalize_path(self, path):
        base_name = os.path.basename(path)
        dir_name = os.path.dirname(path)
        return f"{dir_name}/{base_name}"

    def _normalize_container_name(self, container_name: str) -> str:
        """ Check if the container name is valid. """
        if "\\" in container_name:
            raise InvalidContainerNameError(value=None, driver=self, container_name=container_name)
        if not container_name:
            container_name = "/"
        if not container_name.startswith("/"):
            container_name = "/" + container_name
        if not container_name.endswith("/"):
            container_name += "/"
        return container_name

    def _parent_path(self, path):
        """ Returns path of parent directory or None """
        if path is None or len(path) < 3:
            return None
        dir_path = os.path.dirname(path)
        if not os.path.basename(path):
            dir_path = os.path.dirname(dir_path)
        return dir_path + "/" if len(dir_path) > 1 else dir_path

    def _xml_element_to_object(self, element):
        """ Convert xml item returned by WebDAV into a libcloud Object. """
        try:
            # extract name then convert %20 and + to regular spaces, etc...
            name = xml_prop(element, "href")
            name = urllib.parse.unquote_plus(name)

            extra = {}
            extra["content_type"] = xml_prop(element, "getcontenttype", None)
            extra["creation_time"] = xml_prop(element, "creationdate", "")
            extra["last_modified"] = xml_prop(element, "getlastmodified", None)
            extra["etag"] = xml_prop(element, "getetag")

            if extra["etag"]:
                data_hash = "".join(e for e in extra["etag"] if e.isalnum())

            if not data_hash:
                # Make a hash for the file based on the metadata. We can safely
                # use only the creation_time attribute here. If the file contents change,
                # the underlying file-system will change creation_time.
                data_hash = self._get_hash_function()
                data_hash.update(u(extra["creation_time"]).encode("ascii"))
                data_hash = data_hash.hexdigest()

            if extra["content_type"] == "httpd/unix-directory":
                return Container(name=name, extra=extra, driver=self)

            # extract custom metadata
            metadata = {}
            metadata_elem = element.find(".//{https://analitico.ai}metadata")
            if metadata_elem:
                for child in metadata_elem.getchildren():
                    tag = child.tag.split("}", 1)[1]

                    # deserialize complex items that were serialized to json
                    if tag.endswith("-json"):
                        metadata[tag[:-5]] = json.loads(child.text)
                    else:
                        metadata[tag] = child.text

            return Object(
                name=name,
                size=int(xml_prop(element, "getcontentlength", 0)),
                extra=extra,
                driver=self,
                container=None,
                hash=data_hash,
                meta_data=metadata,
            )
        except Exception as exc:
            raise exc

    def _get_url(self, path):
        path = str(path).strip()
        if path.startswith("/"):
            return self.url + path
        return "".join((self.url, self.cwd, path))

    def _send(self, method, path, expected_code, **kwargs):
        url = self._get_url(path)
        response = self.session.request(method, url, allow_redirects=False, **kwargs)
        if (
            isinstance(expected_code, Number)
            and response.status_code != expected_code
            or not isinstance(expected_code, Number)
            and response.status_code not in expected_code
        ):
            raise WebdavException(method, path, expected_code, response.status_code)
        return response

    def cd(self, path):
        path = path.strip()
        if not path:
            return
        stripped_path = "/".join(part for part in path.split("/") if part) + "/"
        if stripped_path == "/":
            self.cwd = stripped_path
        elif path.startswith("/"):
            self.cwd = "/" + stripped_path
        else:
            self.cwd += stripped_path

    def move(self, path, move_to_path):
        """ Move a file or group of files from their current location to the newly specified path (rename). """
        move_to_path = urllib.parse.urljoin(self.url, move_to_path)
        self._send("MOVE", path, (200, 201, 204), headers={"destination": move_to_path})
        return True

    def mkdir(self, path, safe=False):
        expected_codes = 201 if not safe else (201, 301, 405)
        self._send("MKCOL", path, expected_codes)

    def mkdirs(self, path):
        """ Create directories structure, takes a path or Path object. """
        path = str(path)
        dirs = [d for d in path.split("/") if d]
        if not dirs:
            return
        if path.startswith("/"):
            dirs[0] = "/" + dirs[0]
        old_cwd = self.cwd
        try:
            for dir_path in dirs:
                try:
                    self.mkdir(dir_path, safe=True)
                except Exception as e:
                    if e.actual_code == 409:
                        raise
                finally:
                    self.cd(dir_path)
        finally:
            self.cd(old_cwd)

    def rmdir(self, path, safe=False):
        """ Delete directory with given path. """
        path = str(path).rstrip("/") + "/"
        expected_codes = 204 if not safe else (204, 404)
        self._send("DELETE", path, expected_codes)

    def delete(self, path):
        """ Delete specific file. """
        self._send("DELETE", path, 204)
        return True

    def upload(self, local_path_or_fileobj, remote_path, metadata=None):
        """ Upload a single file from filename or file-like object. """
        if isinstance(local_path_or_fileobj, str):
            with open(local_path_or_fileobj, "rb") as f:
                self._send("PUT", remote_path, (200, 201, 204), data=f)
        else:
            self._send("PUT", remote_path, (200, 201, 204), data=local_path_or_fileobj)

        # store custom properties with object, if the object had some metadata
        # associated with it already it will be overwritten by the new metadata
        self.set_metadata(remote_path, metadata)

    def download(self, remote_path, local_path_or_fileobj):
        response = self._send("GET", remote_path, 200, stream=True)
        if isinstance(local_path_or_fileobj, str) or isinstance(local_path_or_fileobj, Path):
            with open(local_path_or_fileobj, "wb") as f:
                for chunk in response.iter_content(DOWNLOAD_CHUNK_SIZE_BYTES):
                    f.write(chunk)
        else:
            for chunk in response.iter_content(DOWNLOAD_CHUNK_SIZE_BYTES):
                local_path_or_fileobj.write(chunk)

    def download_as_stream(self, remote_path, chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES):
        """ Streaming download of remote path. """
        response = self._send("GET", remote_path, 200, stream=True)
        for chunk in response.iter_content(chunk_size):
            yield chunk

    def ls(self, remote_path):
        """ List given path and return individual item or directory contents as list of Object and Container items. """
        remote_path = self._normalize_path(remote_path)
        headers = {"Depth": "1"}
        response = self._send("PROPFIND", remote_path, (207, 301), headers=headers)

        # follow redirects if content has moved to a new location
        # this will not follow content
        if response.status_code == 301:
            redirect_url = response.headers["location"]
            redirect_path = urlparse(redirect_url).path
            if remote_path != redirect_path:
                return self.ls(redirect_path)
            else:
                raise LibcloudError(f"Content has been moved (301). {response.content}", driver=self)

        tree = xml.fromstring(response.content)
        items = [self._xml_element_to_object(elem) for elem in tree.findall("{DAV:}response")]

        # link objects to parent container
        assert remote_path.startswith("/")
        parent_path = self._parent_path(remote_path)
        if parent_path and parent_path != remote_path:
            parent = Container(parent_path, None, self)
            for item in items:
                if isinstance(item, Object):
                    item.container = parent
        return items

    def exists(self, remote_path: str) -> bool:
        """ Returns True if given path exists on remote server. """
        response = self._send("HEAD", remote_path, (200, 301, 404))
        return True if response.status_code != 404 else False

    def set_metadata(self, remote_path, metadata=None) -> bool:
        """ 
        Apply extra metadata properties to remote_path item (can also be used to clear properties). 
        which are applied as custom properties and then returned in Object.meta_data.
        You can remove metadata by setting metadata to None.
        """
        patch_xml = '<?xml version="1.0" encoding="utf-8" ?>'
        patch_xml += '<dav:propertyupdate xmlns:dav="DAV:" xmlns:analitico="https://analitico.ai">'
        patch_xml += "<dav:set><dav:prop><analitico:metadata>"
        if metadata:
            for key, value in metadata.items():
                key = escape(slugify(key))

                # serialize complex objects to json, key becomes key-json and is deserialized upon read
                if not (isinstance(value, str) or isinstance(value, int)):
                    key = key + "-json"
                    value = json.dumps(value)

                patch_xml += f"<analitico:{key}>{escape(str(value))}</analitico:{key}>"
        patch_xml += "</analitico:metadata></dav:prop></dav:set>"
        patch_xml += "</dav:propertyupdate>"

        # should apply and reply with 207
        self._send("PROPPATCH", remote_path, (200, 207), data=patch_xml)
        # TODO should really check the content of 207 responses and exctract and 500 inside the xml payload
        return True

    ##
    ## StorageDriver utility methods
    ##

    def _make_container(self, container_name: str) -> Container:
        """ Create a container instance (defaults to root directory of server). """
        try:
            container_name = self._normalize_container_name(container_name)
            ls = self.ls(container_name)
            return ls[0]
        except WebdavException as exc:
            raise ContainerDoesNotExistError(value=None, driver=self, container_name=container_name) from exc

    def _make_object(self, container: Container, object_name: str) -> Object:
        """ Create an object instance. """
        try:
            full_path = os.path.join(container.name, object_name)
            ls = self.ls(full_path)
            assert ls and len(ls) == 1 and isinstance(ls[0], Object)
            return ls[0]
        except WebdavException as exc:
            raise ObjectError(value=None, driver=self, object_name=object_name) from exc

    ##
    ## StorageDriver methods
    ##

    def iterate_containers(self):
        """
        Return a generator of containers. This method simulates the behaviour of storage
        on Google Cloud Storage or Amazon S3 where you only have top level buckets by treating
        top level directorties as containers. You can use the ls() method to scan folders, etc.
        :return: A generator of Container instances.
        :rtype: ``generator`` of :class:`Container`
        """
        items = self.ls("/")
        for item in items:
            if isinstance(item, Container):
                yield item

    def iterate_container_objects(self, container):
        """
        Returns a generator of objects for the given container.

        :param container: Container instance
        :type container: :class:`Container`

        :return: A generator of Object instances.
        :rtype: ``generator`` of :class:`Object`
        """
        items = self.ls(container.name)
        for item in items:
            if isinstance(item, Object):
                yield item

    def get_container(self, container_name: str) -> Container:
        """ Return a container instance. """
        return self._make_container(container_name)

    def get_object(self, container_name: str, object_name: str) -> Object:
        """ Return an object instance. """
        container = self._make_container(container_name)
        return self._make_object(container, object_name)

    def download_object(self, obj, destination_path, overwrite_existing=False, delete_on_failure=True):
        """
        Download an object to the specified destination path.

        :param obj: Object instance.
        :type obj: :class:`Object`

        :param destination_path: Full path to a file or a directory where the
                                incoming file will be saved.
        :type destination_path: ``str``

        :param overwrite_existing: True to overwrite an existing file,
            defaults to False.
        :type overwrite_existing: ``bool``

        :param delete_on_failure: True to delete a partially downloaded file if
        the download was not successful (hash mismatch / file size).
        :type delete_on_failure: ``bool``

        :return: True if an object has been successfully downloaded, False
        otherwise.
        :rtype: ``bool``
        """
        if not overwrite_existing and os.path.exists(destination_path):
            raise LibcloudError(
                value=f"{destination_path} already exists, use overwrite_existing=True to replace", driver=self
            )
        self.download(obj.name, destination_path)
        return True

    def download_object_as_stream(self, obj: Object, chunk_size=None) -> object:
        """ Return a generator which yields object's data. """
        full_path = os.path.join(obj.container.name, obj.name)
        yield from self.download_as_stream(full_path, chunk_size)

    def upload_object(
        self, file_path: str, container: Container, object_name: str, extra=None, verify_hash=True
    ) -> Object:
        """ Upload an object currently located on a disk. """
        with open(file_path, "rb") as f:
            return self.upload_object_via_stream(f, container, extra)

    def upload_object_via_stream(
        self, iterator, container: Container, object_name: str, extra=None, header=None
    ) -> Object:
        """
        Upload an object using an iterator.

        If a provider supports it, chunked transfer encoding is used and you
        don't need to know in advance the amount of data to be uploaded.

        Otherwise if a provider doesn't support it, iterator will be exhausted
        so a total size for data to be uploaded can be determined.

        Note: Exhausting the iterator means that the whole data must be
        buffered in memory which might result in memory exhausting when
        uploading a very large object.

        If a file is located on a disk you are advised to use upload_object
        function which uses fs.stat function to determine the file size and it
        doesn't need to buffer whole object in the memory.

        :type iterator: ``object``
        :param iterator: An object which implements the iterator
                         interface and yields binary chunks of data.

        :type container: :class:`Container`
        :param container: Destination container.

        :type object_name: ``str``
        :param object_name: Object name.

        :type extra: ``dict``
        :param extra: (optional) Extra attributes (driver specific). Note:
            This dictionary must contain a 'content_type' key which represents
            a content type of the stored object.

        :rtype: ``object``
        """
        full_path = os.path.join(container.name, object_name)
        directory = os.path.dirname(full_path)
        self.mkdirs(directory)
        self.upload(iterator, full_path, metadata=extra)
        return self._make_object(container, object_name)

    def delete_object(self, obj: Object) -> bool:
        """ Delete an object. """
        full_path = os.path.join(obj.container.name, obj.name)
        self.delete(full_path)
        return True

    def create_container(self, container_name: str) -> Container:
        """
        Create a new container.

        :type container_name: ``str``
        :param container_name: Container name.

        :return: :class:`Container` instance on success.
        :rtype: :class:`Container`
        """
        container_name = self._normalize_container_name(container_name)
        self.mkdirs(container_name)
        return self.get_container(container_name)

    def delete_container(self, container: Container) -> bool:
        """ Delete a container. """
        self.rmdir(container.name)
        return True

    ##
    ## CDN methods are not supported
    ##

    def get_container_cdn_url(self, container, check=False):
        raise NotImplementedError("get_container_cdn_url not implemented for this driver")

    def get_object_cdn_url(self, obj):
        raise NotImplementedError("get_object_cdn_url not implemented for this driver")

    def enable_container_cdn(self, container):
        raise NotImplementedError("enable_container_cdn not implemented for this driver")

    def enable_object_cdn(self, obj):
        raise NotImplementedError("enable_object_cdn not implemented for this driver")
