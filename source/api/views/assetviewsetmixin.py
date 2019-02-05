# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import os

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

from api.models import ItemMixin, Job
from analitico.utilities import logger

##
## AssetViewSetMixin - a mixin for uploading and downloading assets
##

# /assets or /data
ASSET_CLASS_RE = r"(?P<asset_class>(assets|data))$"
# /assets or /data plus a filename with extension
ASSET_ID_RE = r"(?P<asset_class>(assets|data))/(?P<asset_id>[-\w.]{4,256}\.[\w]{1,12})$"
# /assets or /data plus a filename with extension and /info
ASSET_INFO_RE = r"(?P<asset_class>(assets|data))/(?P<asset_id>[-\w.]{4,256}\.[\w]{1,12})/info$"


class AssetViewSetMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to upload, update, download and delete
    /assets associated with the model (eg: source data) and /data, for example the
    processed data resulting from an ETL pipeline or machine learning model.
    """

    # Parse most calls in JSON but also support multipart uploads and forms as well as raw uploads
    parser_classes = (JSONParser, MultiPartParser, FileUploadParser)

    def _asset_upload(self, request, pk, asset_class, asset_id) -> Response:
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
                asset_obj = item._upload_asset_stream(
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
            asset_obj = item._upload_asset_stream(
                iter(request.stream), asset_class, asset_id, content_type=request.content_type, filename=asset_id
            )
            assets.append(asset_obj)
        item.save()
        return Response(assets, status=rest_framework.status.HTTP_201_CREATED)

    def _asset_download(self, request, pk, asset_class, asset_id) -> Response:
        """ Downloads an assets content. """
        # We could use the item's hash as an etag and avoid talking to storage
        # at all if the If-None-Match header matches the etag. However if for
        # whatever reason the asset was modified on the server and our information
        # is out of sync we would skip the download. So we always retrieve the
        # streaming iterator and the latest etag for the cloud asset, then we
        # check the http headers to see if we can skip the download.
        item = self.get_object()
        asset, asset_stream = item._download_asset_stream(asset_class, asset_id)
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

    def _asset_delete(self, request, pk, asset_class, asset_id) -> Response:
        """ Delete asset with given asset_id then return HTTP 204 (No Content). """
        item = self.get_object()
        item._delete_asset(asset_class, asset_id)
        item.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

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
            return self._asset_upload(request, pk, asset_class, asset_id=None)
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
            return self._asset_upload(request, pk, asset_class, asset_id)
        if request.method == "GET":
            assert asset_id
            return self._asset_download(request, pk, asset_class, asset_id)
        if request.method == "DELETE":
            assert asset_id
            return self._asset_delete(request, pk, asset_class, asset_id)
        raise MethodNotAllowed(request.method)

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="asset-detail-info", url_path=ASSET_INFO_RE)
    def asset_detail_info(self, request, pk, asset_class, asset_id):
        """ Returns an asset's details as json. """
        assert asset_class and asset_id
        item = self.get_object()
        asset, _ = item._download_asset_stream(asset_class, asset_id)
        return Response(asset)
