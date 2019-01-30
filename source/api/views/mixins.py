# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import os

from django.utils.text import slugify
from django.http.response import StreamingHttpResponse
from django.utils.http import parse_http_date_safe, http_date
from django.utils.timezone import now

import rest_framework
import rest_framework.viewsets

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import NotFound, MethodNotAllowed, APIException
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser
from rest_framework import status

from api.models import ItemsMixin
from analitico.utilities import logger

# Django Serializers
# https://www.django-rest-framework.org/api-guide/serializers/
# Django ViewSet
# https://www.django-rest-framework.org/api-guide/viewsets/
# Examples of url patterns:
# https://simpleisbetterthancomplex.com/references/2016/10/10/url-patterns.html


class AttributesSerializerMixin:
    """
    A serializer for a generic model which is used to store different kinds of objects. All of them
    have a few fields in common while the rest of the payload is stored in 'json', a dictionary.
    This allows easy extension without having to refactor the SQL storage continuosly and introduce
    new migrations and releases. Also different versions can coexist and ignore extra data.
    """

    def to_representation(self, obj):
        """ Serialize object to dictionary, extracts all json key to main level """
        data = super().to_representation(obj)
        reformatted = {"type": obj.type, "id": data.pop("id"), "attributes": data}
        if obj.attributes:
            for key in obj.attributes:
                data[key] = obj.attributes[key]
        return reformatted

    def to_internal_value(self, data):
        """ Convert dictionary to internal representation (all unknown fields go into json) """
        # If this payload is in json:api format it will have a 'data'
        # element which contains the actual payload. If in json format
        # it will just have a regular dictionary with the data directly in it
        if "data" in data:
            data = data["data"]

        # works with input in json:api style (attributes) or flat json
        attributes = data.pop("attributes") if "attributes" in data else data.copy()

        for (key, _) in self.fields.fields.items():
            if key in attributes:
                data[key] = attributes.pop(key)

        # Perform the data validation, eg:
        # if not blabla:
        #    raise serializers.ValidationError({
        #        'blabla': 'This field is required.'
        #    })
        # Use regular serializer for everything but the json contents which go as-is
        validated = super().to_internal_value(data)
        validated["attributes"] = attributes
        # Return the validated values which will be available as `.validated_data`.
        return validated


##
## AssetsViewSetMixin - a mixin for uploading and downloading assets
##

ASSET_CLASS_RE = r"(?P<asset_class>(assets|data))$"
ASSET_ID_RE = r"(?P<asset_class>(assets|data))/(?P<asset_id>[-\w.]{0,256})$"
ASSET_INFO_RE = r"(?P<asset_class>(assets|data))/(?P<asset_id>[-\w.]{0,256})/info$"


class AssetsViewSetMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to upload, update, download and delete
    /assets associated with the model (eg: source data) and /data, for example the
    processed data resulting from an ETL pipeline or machine learning model.
    """

    # Parse most calls in JSON but also support multipart uploads and forms as well as raw uploads
    parser_classes = (JSONParser, MultiPartParser, FileUploadParser)

    #
    # item/model level help methods
    #

    def _get_asset_path_from_name(self, item, asset_class, asset_id) -> str:
        """
        Given the asset name (eg: /assets/source.csv or /data/train.csv) this method
        will return the full path of the asset based on the item that owns it, for example
        a dataset with a given id, and the workspace that owns the item. A complete path looks like:
        workspaces/ws_001/datasets/ds_001/assets/dataset-asset.csv
        workspaces/ws_001/assets/workspace-asset.csv
        workspaces/ws_001/datasets/ds_001/data/source.csv
        """
        assert asset_class and asset_id and isinstance(item, ItemsMixin)
        if item.workspace:
            w_id = item.workspace.id
            return "workspaces/{}/{}s/{}/{}/{}".format(w_id, item.type, item.id, asset_class, asset_id)
        return "workspaces/{}/{}/{}".format(item.id, asset_class, asset_id)

    def _get_asset_from_id(self, item, asset_class, asset_id, raise404=False) -> dict:
        """ Returns asset record from a model's array of asset descriptors """
        assert isinstance(item, ItemsMixin)
        assets = item.get_attribute(asset_class)
        if assets:
            for asset in item.assets:
                if asset["id"] == asset_id:
                    return asset
        if raise404:
            detail = "{} does not contain {}/{}".format(item, asset_class, asset_id)
            raise NotFound(detail)
        return None

    def _upload_asset_as_stream(self, item, iterator, asset_class, asset_id, size=0, content_type=None, filename=None) -> dict:
        """ Uploads an asset to a model's storage and returns the assets description. """
        assert isinstance(item, ItemsMixin)
        asset_parts = os.path.splitext(asset_id)
        asset_id = slugify(asset_parts[0]) + asset_parts[1]
        asset_path = self._get_asset_path_from_name(item, asset_class, asset_id)

        asset_storage = item.storage
        asset_obj = asset_storage.upload_object_via_stream(iterator, asset_path, extra={"content_type": content_type})

        assets = item.get_attribute(asset_class)
        if not assets:
            assets = []

        asset = self._get_asset_from_id(item, asset_class, asset_id)
        if not asset:
            asset = {"id": asset_id}
            assets.append(asset)

        asset["created_at"] = now().isoformat()
        asset["filename"] = filename
        asset["path"] = asset_path
        asset["hash"] = asset_obj.hash
        asset["content_type"] = content_type
        asset["size"] = max(size, asset_obj.size)

        # update assets in model and therefore on database when caller eventually calls .save()
        item.set_attribute(asset_class, assets)
        return asset

    def _download_asset_as_stream(self, item, asset_class, asset_id):
        """ Returns the asset with the given id along with a stream that can be used to download it from storage. """
        assert isinstance(item, ItemsMixin)
        asset = self._get_asset_from_id(item, asset_class, asset_id, raise404=True)
        asset_storage = item.storage
        storage_obj, storage_stream = asset_storage.download_object_via_stream(asset["path"])

        # update asset with information from storage like etag that can improve browser caching
        if "etag" in storage_obj.extra:
            asset["etag"] = storage_obj.extra["etag"]
        if "last_modified" in storage_obj.extra:
            asset["last_modified"] = storage_obj.extra["last_modified"]
        asset["size"] = storage_obj.size
        asset["hash"] = storage_obj.hash
        return asset, storage_stream

    def _delete_asset(self, item, asset_class, asset_id) -> dict:
        """ Deletes asset with given asset_id and returns its details. Will raise NotFound if asset_id is invalid. """
        assert asset_class and asset_id and isinstance(item, ItemsMixin)
        assets = item.get_attribute(asset_class)
        asset = self._get_asset_from_id(item, asset_class, asset_id, raise404=True)

        storage = item.storage
        deleted = storage.delete_object(asset["path"])

        if not deleted:
            # TODO if object cannot deleted it may be better to leave orphan in storage and proceed to deleting from assets?
            message = "Cannot delete {}/{} from storage, try again later.".format(asset_class, asset_id)
            logger.error(message)
            raise APIException(detail=message, code=status.HTTP_503_SERVICE_UNAVAILABLE)

        assets.remove(asset)
        item.set_attribute(asset_class, assets)
        return asset

    #
    # viewset level help methods
    #

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
                asset_obj = self._upload_asset_as_stream(
                    item, iter(upload), asset_class, asset_id, size=upload.size, content_type=content_type, filename=upload.name
                )
                assets.append(asset_obj)
        else:
            # simple upload without a Content-Disposition header. filename is unknown
            asset_obj = self._upload_asset_as_stream(
                item, iter(request.stream), asset_class, asset_id, content_type=request.content_type, filename=asset_id
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
        asset, asset_stream = self._download_asset_as_stream(item, asset_class, asset_id)
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
        self._delete_asset(item, asset_class, asset_id)
        item.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    #
    # ViewSet actions
    #

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="asset-list", url_path=ASSET_CLASS_RE)
    def assets_list(self, request, pk, asset_class) -> Response:
        """ Returns a listing of all assets associated with this item. """
        item = self.get_object()
        return Response(item.get_attribute(asset_class, []))

    @permission_classes((IsAuthenticated,))
    @action(methods=["get", "post", "put", "delete"], detail=True, url_name="asset-detail", url_path=ASSET_ID_RE)
    def asset_detail(self, request, pk, asset_class, asset_id=None) -> Response:
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

    # TODO make asset_id portion of regex mandatory
    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="asset-detail-info", url_path=ASSET_INFO_RE)
    def asset_detail_info(self, request, pk, asset_class, asset_id):
        """ Returns an asset's details as json. """
        item = self.get_object()
        asset, _ = self._download_asset_as_stream(item, asset_class, asset_id)
        return Response(asset)
