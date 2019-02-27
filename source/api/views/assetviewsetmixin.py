# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import os
import pandas as pd

from django.utils.text import slugify
from django.http.response import StreamingHttpResponse
from django.utils.http import parse_http_date_safe, http_date
from django.utils.timezone import now
from django.urls import reverse

import rest_framework
import rest_framework.viewsets

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import NotFound, MethodNotAllowed, APIException
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser
from rest_framework import status

from analitico.utilities import logger, get_csv_row_count
from api.models import ItemMixin, Job, ASSETS_CLASS_DATA
from api.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE
from api.utilities import get_query_parameter, get_query_parameter_as_bool
from api.factory import ServerFactory

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
        page = int(request.GET.get("page", 0))
        page_size = max(MIN_PAGE_SIZE, min(MAX_PAGE_SIZE, int(request.GET.get("page_size", DEFAULT_PAGE_SIZE))))
        offset = page * page_size

        # retrieve only the requested chunk from cached copy of storage asset on local disk
        with ServerFactory(request=request) as factory:
            item = self.get_object()

            asset_file = factory.get_cache_asset(item, asset_class, asset_id)
            df = pd.read_csv(asset_file, skiprows=range(1, offset + 1), nrows=page_size)
            df = df.fillna("")  # for now replace NaN with empty string

            data = {
                "meta": {"page": page, "page_records": len(df), "page_size": page_size},
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
