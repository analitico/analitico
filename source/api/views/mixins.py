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

    def get_item_url(self, item):
        """ Returns absolute url to given asset using the same endpoint the request came in through """
        url = reverse("api:" + item.type + "-detail", args=(item.id,))
        request = self.context.get("request")
        if request:
            url = request.build_absolute_uri(url)
        return url

    def get_item_asset_url(self, item, asset_class, asset_id):
        """ Returns absolute url to given item's asset """
        url = reverse("api:" + item.type + "-asset-detail", args=(item.id, asset_class, asset_id))
        request = self.context.get("request")
        if request:
            url = request.build_absolute_uri(url)
        return url

    def get_item_links(self, item):
        """ Returns link to item and related assets in a json:api compliant dictionary """
        links = {"self": self.get_item_url(item)}
        if item.workspace:
            links["workspace"] = self.get_item_url(item.workspace)
        for asset_class in ("assets", "data"):
            assets = item.get_attribute(asset_class)
            if assets:
                for asset in assets:
                    asset_url = self.get_item_asset_url(item, asset_class, asset["id"])
                    links[asset_class + "/" + asset["id"]] = asset_url
        return links

    def to_representation(self, item):
        """ Serialize object to dictionary, extracts all json key to main level """
        data = super().to_representation(item)
        reformatted = {"type": item.type, "id": data.pop("id"), "attributes": data}
        if item.attributes:
            for key in item.attributes:
                data[key] = item.attributes[key]
        # add links to self and its assets
        reformatted["links"] = self.get_item_links(item)
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
ASSET_ID_RE = r"(?P<asset_class>(assets|data))/(?P<asset_id>[-\w.]{4,256})$"
ASSET_INFO_RE = r"(?P<asset_class>(assets|data))/(?P<asset_id>[-\w.]{4,256})/info$"


class AssetsViewSetMixin:
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


##
## JobsViewSetMixin - endpoints for creating jobs attached to an item, eg: train a model
##

from .jobviews import JobSerializer


class JobsViewSetMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to create jobs that are applied to the item,
    for example create a job that will process a dataset or train a model.
    The mixin also lets you list jobs attached to the item or see the status of a specific job.
    """

    # defined in subclass to list acceptable actions
    job_actions = ()

    def _create_job(self, request, job_item, job_action):
        workspace_id = job_item.workspace.id if job_item.workspace else job_item.id
        job_action = job_item.type + "/" + job_action
        job = Job(item_id=job_item.id, action=job_action, workspace_id=workspace_id, status=Job.JOB_STATUS_PROCESSING)
        job.save()
        job.run(request)
        return job

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="job-list", url_path="jobs")
    def job_list(self, request, pk) -> Response:
        """ Returns a listing of all jobs associated with this item. """
        jobs = Job.objects.filter(item_id=pk)
        jobs_serializer = JobSerializer(jobs, many=True)
        return Response(jobs_serializer.data)

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="job-detail", url_path=r"jobs/(?P<job_action>[-\w.]{4,256})$")
    def job_create(self, request, pk, job_action) -> Response:
        """ Creates a job for this item and returns it. """
        job_item = self.get_object()
        if job_action in self.job_actions:
            job = self._create_job(request, job_item, job_action)
            jobs_serializer = JobSerializer(job)
            return Response(jobs_serializer.data)
        raise MethodNotAllowed(job_item.type + " cannot create a job of type: " + job_action)
