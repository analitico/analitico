# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import os
import pandas as pd
import urllib
import io

from django.http.response import StreamingHttpResponse
from django.utils.http import parse_http_date_safe, http_date

import rest_framework
import rest_framework.viewsets

from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser
from rest_framework.serializers import Serializer

from analitico import ACTION_PROCESS, AnaliticoException
from analitico.utilities import get_csv_row_count
from api.models import Dataset, Workspace
from api.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE, PAGE_PARAM, PAGE_SIZE_PARAM
from api.utilities import get_query_parameter, get_query_parameter_as_bool
from api.factory import ServerFactory

import libcloud
import api.libcloud

from libcloud.storage.base import StorageDriver

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
## AssetViewSetMixin - a mixin for uploading and downloading assets
##

# /assets or /data
ASSET_CLASS_RE = r"(?P<asset_class>(assets|data))$"
# /assets or /data plus a filename with extension
ASSET_ID_RE = r"(?P<asset_class>(assets|data))/(?P<asset_id>[-\w.]{1,256}\.[\w]{1,12})$"
# /assets or /data plus a filename with extension and /info
ASSET_INFO_RE = r"(?P<asset_class>(assets|data))/(?P<asset_id>[-\w.]{1,256}\.[\w]{1,12})/info$"


class AssetViewSetMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to upload, update, download and delete
    /assets associated with the model (eg: source data) and /data, for example the
    processed data resulting from an ETL pipeline or machine learning model.
    """

    # Parse most calls in JSON but also support multipart uploads and forms as well as raw uploads
    parser_classes = (JSONParser, MultiPartParser, FileUploadParser)

    def asset_upload(self, request, pk, asset_class, asset_id) -> Response:
        """ 
        Uploads one or more assets to this item's storage, returns a list of 
        uploaded assets. Supports direct upload and multipart forms. 
        """
        item = self.get_object()
        assets = []

        if request.FILES:
            # one or more files have been uploaded using a multipart form or
            # a single file has been posted with a Content-Disposition header
            # indicating the original filename
            for upload in request.FILES.values():
                content_type = upload.content_type
                # only text/* needs charset attributes
                # https://www.w3.org/International/articles/http-charset/index
                if content_type.startswith("text/") and upload.charset:
                    content_type = content_type + "; charset=" + upload.charset
                if not asset_id or len(request.FILES) > 1:
                    asset_id = upload.name
                asset_obj = item.upload_asset_stream(
                    iter(upload),
                    asset_class,
                    asset_id,
                    size=upload.size,
                    content_type=content_type,
                    filename=upload.name,
                )
                assets.append(asset_obj)
        else:
            # simple upload without a Content-Disposition header. filename is unknown
            asset_obj = item.upload_asset_stream(
                iter(request.stream), asset_class, asset_id, content_type=request.content_type, filename=asset_id
            )
            assets.append(asset_obj)
        item.save()

        # when an asset is uploaded to a Dataset we will start a job to process the dataset (async).
        # if this job is not requested, the caller can add ?process=false and the job will not be started
        if isinstance(item, Dataset):
            process = get_query_parameter_as_bool(self.request, "process", True)
            if process:
                # job_id is added automatically to the dataset and reported in
                # the response as a "related" item with a link to the job itself
                item.create_job(ACTION_PROCESS)

        return Response(assets, status=rest_framework.status.HTTP_201_CREATED)

    def asset_download(self, request, pk, asset_class, asset_id) -> Response:
        """ Downloads an assets content. """
        # We could use the item's hash as an etag and avoid talking to storage
        # at all if the If-None-Match header matches the etag. However if for
        # whatever reason the asset was modified on the server and our information
        # is out of sync we would skip the download. So we always retrieve the
        # streaming iterator and the latest etag for the cloud asset, then we
        # check the http headers to see if we can skip the download.
        item = self.get_object()
        asset, asset_stream = item.download_asset_stream(asset_class, asset_id)
        # if cloud storage provides an etag (optional) let's use that, otherwise the hash will do
        etag = asset["etag"] if "etag" in asset else '"' + asset["hash"] + '"'
        last_modified = parse_http_date_safe(asset["last_modified"]) if "last_modified" in asset else None
        # if content has not changed cut the response short and avoid streaming data
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-Modified-Since
        is_304 = "HTTP_IF_NONE_MATCH" in request.META and request.META["HTTP_IF_NONE_MATCH"] == etag
        if not is_304 and last_modified and "HTTP_IF_MODIFIED_SINCE" in request.META:
            if_modified_since = parse_http_date_safe(request.META["HTTP_IF_MODIFIED_SINCE"])
            is_304 = if_modified_since >= last_modified
        if is_304:
            response = Response(status=status.HTTP_304_NOT_MODIFIED, content_type=asset["content_type"])
            if last_modified:
                response["Last-Modified"] = http_date(last_modified)
            response["ETag"] = etag
            return response
        response = StreamingHttpResponse(asset_stream, content_type=asset["content_type"])
        if last_modified:
            response["Last-Modified"] = http_date(last_modified)
        if int(asset["size"]) > 0:
            response["Content-Length"] = str(asset["size"])
        response["ETag"] = etag
        return response

    def asset_delete(self, request, pk, asset_class, asset_id) -> Response:
        """ Delete asset with given asset_id then return HTTP 204 (No Content). """
        item = self.get_object()
        item._delete_asset(asset_class, asset_id)
        item.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def asset_download_csv_as_json_with_paging(self, request, pk, asset_class, asset_id):
        """ Returns a .csv asset converted to json records with paging support """
        # which page are we on, what size is each page
        page = int(request.GET.get(PAGE_PARAM, 0))
        page_size = max(MIN_PAGE_SIZE, min(MAX_PAGE_SIZE, int(request.GET.get(PAGE_SIZE_PARAM, DEFAULT_PAGE_SIZE))))
        offset = page * page_size

        # retrieve only the requested chunk from cached copy of storage asset on local disk
        with ServerFactory(request=request) as factory:
            item = self.get_object()

            asset_file = factory.get_cache_asset(item, asset_class, asset_id)
            df = pd.read_csv(asset_file, skiprows=range(1, offset + 1), nrows=page_size)
            df = df.fillna("")  # for now replace NaN with empty string

            data = {
                "meta": {PAGE_PARAM: page, "page_records": len(df), PAGE_SIZE_PARAM: page_size},
                "data": df.to_dict("records"),
            }

            # extra metadata could be expensive so we leave the option to opt out for performance
            if get_query_parameter_as_bool(request, "meta", True):
                rows = get_csv_row_count(asset_file)  # file needs to be read end to end
                data["meta"]["total_pages"] = int((rows + page_size - 1) / page_size)
                data["meta"]["total_records"] = rows
            # return records and information on current page
            return Response(data)

    #
    # ViewSet actions
    #

    @permission_classes((IsAuthenticated,))
    @action(methods=["get", "post", "put"], detail=True, url_name="asset-list", url_path=ASSET_CLASS_RE)
    def assets_list(self, request, pk, asset_class) -> Response:
        """ Returns a listing of all assets associated with this item. """
        assert asset_class in ("assets", "data")
        if request.method in ("POST", "PUT"):
            # asset_id can be null, for example, when uploading multiple files at once
            return self.asset_upload(request, pk, asset_class, asset_id=None)
        if request.method == "GET":
            item = self.get_object()
            return Response(item.get_attribute(asset_class, []))
        raise MethodNotAllowed(request.method)

    @permission_classes((IsAuthenticated,))
    @action(methods=["get", "post", "put", "delete"], detail=True, url_name="asset-detail", url_path=ASSET_ID_RE)
    def asset_detail(self, request, pk, asset_class, asset_id) -> Response:
        """ Upload, update, download or delete a file asset associated with this item. Supports both direct upload and multipart forms. """
        assert asset_class in ("assets", "data")
        if request.method in ("POST", "PUT"):
            # asset_id can be null when uploading multiple files at once with multipart encoding
            return self.asset_upload(request, pk, asset_class, asset_id)
        if request.method == "GET":
            assert asset_id
            # if this is a .csv asset which is being requested as a paged json dictionary
            if get_query_parameter(request, "format") == "json" and ".csv" in asset_id:
                return self.asset_download_csv_as_json_with_paging(request, pk, asset_class, asset_id)
            # download asset directly
            return self.asset_download(request, pk, asset_class, asset_id)
        if request.method == "DELETE":
            assert asset_id
            return self.asset_delete(request, pk, asset_class, asset_id)
        raise MethodNotAllowed(request.method)

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="asset-detail-info", url_path=ASSET_INFO_RE)
    def asset_detail_info(self, request, pk, asset_class, asset_id):
        """ Returns an asset's details as json. """
        assert asset_class and asset_id
        item = self.get_object()
        asset, _ = item.download_asset_stream(asset_class, asset_id)
        return Response(asset)

    ##
    ## /files endpoint lists files on remote endpoint
    ##

    def files_metadata(self, request, pk, url, driver, base_path):
        # return metadata for files and directories
        assert base_path and base_path.endswith("/")
        if request.method in ["GET"]:
            items = driver.ls(os.path.join(base_path, url))
            for item in items:
                item.name = item.name.replace(base_path[:-1], "")
            base_url = request.build_absolute_uri()
            serializer = LibcloudStorageItemsSerializer(items, many=True, base_url=base_url)
            return Response(serializer.data, content_type="json")

        # modify metadata, rename, add custom metadata
        if request.method in ["PUT", "POST"]:
            data = request.data["data"]

            # is this a rename request? id/path is being updated
            if url != data["id"]:
                driver.move(url, data["id"])
                return Response(status=status.HTTP_201_CREATED)

            # TODO update extras if changed

        msg = f"Method {request.method} on {request.path} is not implemented"
        raise AnaliticoException(msg, status_code=status.HTTP_400_BAD_REQUEST)

    def files_raw(self, request, pk, driver, path):
        folder_path = path[: path.rfind("/") + 1]
        is_folder = folder_path != path
        is_root = folder_path == "/"

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
            driver.upload(data, path, extra=None)
            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == "MOVE":
            # TODO move directories?
            move_to_path = request["Destination"]
            driver.move(path, move_to_path)
            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == "DELETE":
            # TODO delete directories
            driver.delete(path)
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
        workspace = item if isinstance(item, Workspace) else item.workspace

        driver = workspace.storage.driver
        if not isinstance(driver, api.libcloud.WebdavStorageDriver):
            raise AnaliticoException(
                "/files is only supported on WebDAV based storage", status_code=status.HTTP_501_NOT_IMPLEMENTED
            )

        # TODO check specific webdav permissions?

        base_path = "/" if isinstance(item, Workspace) else f"/{item.type}s/{item.id}/"
        url = base_path + url
        metadata = get_query_parameter_as_bool(request, "metadata")

        if metadata:
            # operate on files metadata
            return self.files_metadata(request, pk, url, driver, base_path)

        # operations on raw files (uploading, downloading, deleting, etc)
        return self.files_raw(request, pk, driver, url)
