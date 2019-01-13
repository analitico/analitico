
# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import collections

from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import StreamingHttpResponse

import rest_framework

from rest_framework import serializers, exceptions, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError, MethodNotAllowed
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser

from api.models import ItemsMixin, Workspace, Dataset, Recipe
from analitico.utilities import logger, get_dict_dot
from api.utilities import time_ms, api_get_parameter, api_check_authorization

import analitico.models
import analitico.utilities
import analitico.storage

import api.models
import api.utilities
import api.serializers

##
## ViewSetMixin - shared features
##

# https://stackoverflow.com/questions/50425262/django-rest-framework-pass-extra-parameter-to-actions
# contact = get_object_or_404(self.get_queryset(), pk=pk)

# Examples of url patterns:
# https://simpleisbetterthancomplex.com/references/2016/10/10/url-patterns.html

class ItemViewSetMixin():

    # Parse most calls in JSON but also support multipart uploads and forms as well as raw uploads
    parser_classes = (JSONParser, MultiPartParser, FileUploadParser, )

    ##
    ## Assets - listing, uploading, downloading, deleting
    ##

    def _asset_upload(self, request, pk, asset_id):
        """ Uploads one or more assets to this item's storage, returns list of uploaded assets. Supports direct upload and multipart forms. """
        item = self.get_object()
        assets = []

        # one or more files have been uploaded using a multipart form or
        # a single file has been posted with a Content-Disposition header
        # indicating the original filename
        if request.FILES:
            for upload in request.FILES.values():
                content_type = upload.content_type
                # only text/* needs charset attributes
                # https://www.w3.org/International/articles/http-charset/index
                if content_type.startswith('text/') and upload.charset:
                    content_type = content_type + '; charset=' + upload.charset

                if not asset_id or len(request.FILES) > 1:
                    asset_id = upload.name 
                asset_obj = item.upload_asset_via_stream(iter(upload), asset_id, size=upload.size, content_type=content_type, filename=upload.name)
                assets.append(asset_obj)

        # simple upload without a Content-Disposition header. filename is unknown
        else:
            asset_obj = item.upload_asset_via_stream(iter(request.stream), asset_id, content_type=request.content_type, filename=asset_id)
            assets.append(asset_obj)

        item.save()
        return Response(assets, status=rest_framework.status.HTTP_201_CREATED)


    def _asset_download(self, request, pk, asset_id):
        """ Downloads an assets content. """
        item = self.get_object()
        asset, asset_stream = item.download_asset_as_stream(asset_id)

        # if content has not changed cut the response short and avoid streaming data
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag
        # if 'etag' in asset and request.etag == asset['etag']:
        #    return Response(status=status.HTTP_304_NOT_MODIFIED)

        response = StreamingHttpResponse(asset_stream, content_type=asset['content_type'])
        if 'etag' in asset: response['etag'] = asset['etag']
        if 'last_modified' in asset: response['last_modified'] = asset['last_modified']
        return response


    def _asset_delete(self, request, pk, asset_id):
        raise MethodNotAllowed('DELETE')


    @action(methods=['get'], detail=True, url_name='asset-list', url_path='assets')
    def assets(self, request, pk):
        """ Returns a listing of all assets associated with this item. """
        item = self.get_object()
        return Response(item.assets)


    @action(methods=['get', 'post', 'put', 'delete'], detail=True, url_name='asset-detail', url_path=r'assets/(?P<asset_id>[-\w.]{0,256})$')
    def asset(self, request, pk, asset_id=None):
        """ Upload, update, download or delete a file asset associated with this item. Supports both direct upload and multipart forms. """
        if request.method == 'POST' or request.method == 'PUT':
            return self._asset_upload(request, pk, asset_id)
        if request.method == 'GET':
            return self._asset_download(request, pk, asset_id)
        if request.method == 'DELETE':
            return self._asset_delete(request, pk, asset_id)
        raise MethodNotAllowed(request.method)


##
## WorkspaceViewSet - list, detail, post and update workspaces
## 

class WorkspaceViewSet(ItemViewSetMixin, viewsets.ModelViewSet):
    """ 
    List, detail, create, update and delete machine learning project trainings. 
    
    retrieve: Retrieve a specific project.
    list: Retrieve a list of projects for the user.
    create: Create a new project for the user.
    update: Update a previously created project.
    partial_update: Modify a previously created project.
    delete: Delete a project.
    """

    item_class = api.models.Workspace
    serializer_class = api.serializers.WorkspaceSerializer

    help_text='help text viewset'
    label ='viewset label'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Workspace.objects.all()
        return Workspace.objects.filter(user=self.request.user)


##
## DatasetViewSet - list, detail, post and update datasets
##

class DatasetViewSet(ItemViewSetMixin, viewsets.ModelViewSet):

    item_class = api.models.Dataset
    serializer_class = api.serializers.DatasetSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Dataset.objects.all()
        return Dataset.objects.filter(workspace__user=self.request.user)
