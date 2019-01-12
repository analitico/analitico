
# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import collections

from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist

import rest_framework
from rest_framework import serializers
from rest_framework import exceptions
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError
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

#    parser_classes = (JSONParser, MultiPartParser, FileUploadParser, )
    parser_classes = (JSONParser, MultiPartParser, FileUploadParser, )

    @action(methods=['post', 'put'], detail=False, url_path='prova002/(?P<pk2>[^/.]+)$')
    def prova002(self, request, pk=None, pk2=None):
        return Response({ 'filename': pk2 })

    ##
    ## Assets - listing, uploading, downloading, deleting
    ##

    @action(methods=['get'], detail=True, url_name='asset-list', url_path='assets')
    def assets(self, request, pk):
        item = self.get_object()
        return Response(item.assets)


    @action(methods=['post', 'put'], detail=True, url_name='asset-detail', url_path='assets/(?P<filename>[-\w.]{0,256})$')
    def upload_asset(self, request, pk, filename=None):
        """ Uploads one or more assets to this item's storage using direct upload or a multipart form with a number of files in it. Returns list of uploaded assets. """
        item = self.get_object()
        assets = []

        if request.FILES:
            for upload in request.FILES.values():
                content_type = upload.content_type
                if upload.charset:
                    content_type = content_type + '; charset=' + upload.charset

                asset_name = filename if filename and len(request.FILES) < 2 else upload.name
                # TODO when uploading a file (not a multipart for with a file inside) the line below fails on upload.file.file
                asset_obj = item.upload_asset_via_stream(upload.file.file, asset_name, size=upload.size, content_type=content_type)
                assets.append(asset_obj)

        item.save()
        return Response(assets, status=rest_framework.status.HTTP_201_CREATED)


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
