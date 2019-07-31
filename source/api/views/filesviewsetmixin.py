# pylint: disable=no-member

import os
import pandas as pd
import urllib
import io

from pathlib import Path
from django.http.response import StreamingHttpResponse

from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, permission_classes
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser
from rest_framework.serializers import Serializer

from analitico import AnaliticoException, PARQUET_SUFFIXES, CSV_SUFFIXES, EXCEL_SUFFIXES, HDF_SUFFIXES, PANDAS_SUFFIXES, ORDER_PARAM, QUERY_PARAM
from analitico.pandas import pd_read_csv
from analitico.utilities import get_dict_dot

from api.models import Workspace
from api.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE, PAGE_PARAM, PAGE_SIZE_PARAM
from api.utilities import get_query_parameter_as_bool, get_query_parameter_as_int, get_query_parameter

import libcloud
import api.libcloud

from libcloud.storage.base import Object

import api.metadata


##
## FilesSerializer
##


class LibcloudStorageItemsSerializer(Serializer):
    """ Serialize, deserialize libcloud Object and Container. """

    def __init__(self, *args, base_url=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = base_url

    def to_representation(self, instance):
        if isinstance(instance, libcloud.storage.base.Object):
            d = {
                "type": "analitico/file",
                "id": instance.name,
                "attributes": {"hash": instance.hash, "size": instance.size, **instance.extra},
                "links": {"self": urllib.parse.urljoin(self.base_url, instance.name)},
            }
            if instance.meta_data:
                d["attributes"]["metadata"] = instance.meta_data
            return d

        if isinstance(instance, libcloud.storage.base.Container):
            return {
                "type": "analitico/directory",
                "id": instance.name,
                "attributes": {**instance.extra},
                "links": {"self": urllib.parse.urljoin(self.base_url, instance.name)},
            }

        raise NotImplementedError(f"Can't serialize {instance}")


##
## FilesViewSetMixin - a mixin for uploading and downloading assets
##


class FilesViewSetMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to upload, update, download and delete
    /files associated with the model (eg: csv, notebooks, etc). ?metadata=true can be
    used to retrieve information on the files. ?records=true can be used to extract
    records from large data files as paged json data.
    """

    # Parse most calls in JSON but also support multipart uploads and forms as well as raw uploads
    parser_classes = (JSONParser, MultiPartParser, FileUploadParser)

    ##
    ## ?records=True - methods used to access data files records
    ##

    def files_records(self, request, pk, item, url, driver, base_path):
        # return metadata for files and directories
        assert base_path and base_path.endswith("/")
        if request.method != "GET":
            raise AnaliticoException(
                "/files/ with ?records=true only supports GET", status_code=status.HTTP_400_BAD_REQUEST
            )

        # retrieve metadata, refresh if needed
        path = os.path.join(base_path, url)
        metadata = api.metadata.get_file_metadata(driver, path, refresh=True)

        # which page are we on, what size is each page? should we filter rows?
        page = get_query_parameter_as_int(request, PAGE_PARAM, 0)
        page_size = max(
            MIN_PAGE_SIZE, min(MAX_PAGE_SIZE, get_query_parameter_as_int(request, PAGE_SIZE_PARAM, DEFAULT_PAGE_SIZE))
        )

        query = get_query_parameter(request, QUERY_PARAM, None) # ?query=
        sort = get_query_parameter(request, ORDER_PARAM, None) # ?order=

        # retrieve data and filter it if requested
        df, rows = api.metadata.get_file_dataframe(driver, path, page, page_size, query, sort)
        df = df.fillna("")  # replace NaN with empty string

        # add paging metadata
        rows = rows if rows else int(metadata["total_records"])
        metadata[PAGE_PARAM] = page
        metadata["page_records"] = len(df)
        metadata[PAGE_SIZE_PARAM] = page_size
        metadata["total_pages"] = int((rows + page_size - 1) / page_size)
        metadata["total_records"] = rows

        data = {"meta": metadata, "data": df.to_dict("records")}

        # return records and information on current page
        return Response(data)

    ##
    ## ?metadata=true - methods used to retrieve information on the files (as opposed to file contents)
    ##

    def files_metadata(self, request, pk, url, driver, base_path):
        # return metadata for files and directories
        assert base_path and base_path.endswith("/")
        assert url and url.startswith("/")

        if request.method in ["GET"]:
            try:
                path = os.path.join(base_path, url)
                items = driver.ls(path)
            except api.libcloud.WebdavException as exc:
                raise AnaliticoException(f"Can't get information on {path}", status_code=exc.actual_code) from exc

            # refreshing metadata?
            refresh = get_query_parameter_as_bool(request, "refresh", False)

            for item in items:
                # append analitico's metadata to webdav's metadata
                metadata = api.metadata.get_file_metadata(driver, item.name, refresh=refresh)
                if metadata:
                    if item.meta_data:
                        for key, value in metadata:
                            item.meta_data[key] = value
                    else:
                        item.meta_data = metadata

            for item in items:
                item.name = item.name.replace(base_path[:-1], "")

            base_url = request.build_absolute_uri()
            serializer = LibcloudStorageItemsSerializer(items, many=True, base_url=base_url)
            return Response(serializer.data)

        # modify metadata, rename, add custom metadata
        if request.method in ["PUT", "POST"]:
            data = request.data["data"]

            # schema has changes?
            old_schema = get_dict_dot(api.metadata.get_file_metadata(driver, url), "schema")
            new_schema = get_dict_dot(data, "attributes.metadata.schema")
            if new_schema == old_schema:
                # new schema same as old, don't convert
                new_schema = None

            # is this a rename/move request? id/path is being updated
            # this is equivalent to webdav's move http method which we
            # cannot use because django's middleware filters out move
            # as an http method/verb
            new_path = url
            if url != data["id"]:
                assert data["id"].startswith("/"), "Path should start with slash, eg: /file.txt"
                new_path = base_path + data["id"][1:]

                # are we changing format?
                src_suffix = Path(url).suffix
                dst_suffix = Path(new_path).suffix
                if src_suffix != dst_suffix:
                    # we support limited formats for data conversions
                    if not (src_suffix in PANDAS_SUFFIXES and dst_suffix in PANDAS_SUFFIXES):
                        msg = f"Can't convert {src_suffix} to {dst_suffix}"
                        raise AnaliticoException(msg, status_code=status.HTTP_400_BAD_REQUEST)

                    # converting a file format and potentially changing its schema at once
                    api.metadata.apply_conversions(driver, url, new_path=new_path, new_schema=new_schema)
                    return Response(status=status.HTTP_201_CREATED)

            if new_schema:
                # changing schema and moving without converting formats
                api.metadata.apply_conversions(driver, url, new_path=new_path, new_schema=new_schema)
                return Response(status=status.HTTP_201_CREATED)
            elif url != new_path:
                # moving files without any conversions
                driver.move(url, new_path)
                return Response(status=status.HTTP_201_CREATED)

            return Response(status=status.HTTP_200_OK)

        msg = f"Method {request.method} on {request.path} is not implemented"
        raise AnaliticoException(msg, status_code=status.HTTP_400_BAD_REQUEST)

    ##
    ## /files endpoint lists files on remote endpoint, provides metadata, records, etc.
    ##

    def files_raw(self, request, pk, driver, path):
        folder_path = path[: path.rfind("/") + 1]
        # is_folder = folder_path != path
        # is_root = folder_path == "/"

        if request.method in ["GET"]:
            # streaming download of a single file from storage
            try:
                ls = driver.ls(path)
            except api.libcloud.WebdavException as exc:
                raise AnaliticoException(f"Can't get information on {path}", status_code=exc.actual_code) from exc

            if len(ls) > 1:
                metadata_url = request.build_absolute_uri()
                metadata_msg = f"Can only download a file at a time, get information on a directory with {metadata_url}"
                raise AnaliticoException(metadata_msg, status_code=status.HTTP_400_BAD_REQUEST)

            obj_ls = ls[0]
            obj_stream = driver.download_as_stream(path)
            response = StreamingHttpResponse(obj_stream, content_type=obj_ls.extra["content_type"])
            response["Last-Modified"] = obj_ls.extra["last_modified"]
            response["ETag"] = obj_ls.extra["etag"]

            # add amazon compatible metadata headers if any
            metaheaders = api.libcloud.metadata_to_amz_meta_headers(obj_ls.meta_data)
            for key, value in metaheaders.items():
                response[key] = value

            if obj_ls.size > 0:
                response["Content-Length"] = str(obj_ls.size)
            return response

        if request.method in ["PUT", "POST"]:
            # create directory if it doesn't exist (similar to cloud storage)
            driver.mkdirs(folder_path)

            # upload or replace existing files in storage
            # TODO extract metadata from custom headers, if any
            # TODO stream content
            if request.FILES:
                files = list(request.FILES.values())
                if len(files) > 1:
                    raise AnaliticoException(
                        "You cannot upload multiple files at once.", status=status.HTTP_400_BAD_REQUEST
                    )
                # read data directly from file that django saved somewhere
                data = iter(files[0])
            else:
                data = io.StringIO(request.data)

            # upload, overwrite if there and reset metadata if any
            driver.upload(data, path, metadata=None)
            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == "DELETE":
            try:
                driver.delete(path)
            except api.libcloud.WebdavException as exc:
                raise AnaliticoException(f"Can't delete {path}", status_code=exc.actual_code) from exc
            return Response(status=status.HTTP_204_NO_CONTENT)

        # some combinations of methods and urls are not supported
        msg = f"Method {request.method} on {request.path} is not implemented"
        raise AnaliticoException(msg, status_code=status.HTTP_400_BAD_REQUEST)

    @permission_classes((IsAuthenticated,))
    @action(methods=["get", "post", "put", "delete"], detail=True, url_name="files", url_path="files/(?P<url>.*)")
    def files(self, request, pk, url) -> Response:
        """
        List properties of files and directory in storage associated with a given workspace, recipe or dataset.
        The url parameter can be omitted to obtain files in the root directory of the given item or it can be used
        to navigate subdirectories, etc. Each item reported in data represents a single directory or file. The related
        link points to the webdav url where the item can be downloaded from, uploaded to or deleted.
        """
        item = self.get_object()
        # TODO check specific webdav permissions?

        workspace = item if isinstance(item, Workspace) else item.workspace

        driver = workspace.storage.driver
        if not isinstance(driver, api.libcloud.WebdavStorageDriver):
            raise AnaliticoException(
                "/files is only supported on WebDAV based storage", status_code=status.HTTP_501_NOT_IMPLEMENTED
            )

        # path of this file (or directory) in storage
        base_path = "/" if isinstance(item, Workspace) else f"/{item.type}s/{item.id}/"
        url = base_path + url

        # requesting file metadata instead of the file itself?
        metadata = get_query_parameter_as_bool(request, "metadata", False)
        if metadata:
            return self.files_metadata(request, pk, url, driver, base_path)

        # requesting data records instead of the file itself?
        records = get_query_parameter_as_bool(request, "records", False)
        if records:
            return self.files_records(request, pk, item, url, driver, base_path)

        # operations on raw files (uploading, downloading, deleting, etc)
        return self.files_raw(request, pk, driver, url)
