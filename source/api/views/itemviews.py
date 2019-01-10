
# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import collections

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

from api.models import AttributesMixin, Workspace, Dataset, Recipe
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

class ViewSetMixin():
    pass


##
## WorkspaceViewSet - list, detail, post and update workspaces
## 

class WorkspaceViewSet(ViewSetMixin, viewsets.ModelViewSet):
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

class DatasetViewSet(ViewSetMixin, viewsets.ModelViewSet):

    item_class = api.models.Dataset
    serializer_class = api.serializers.DatasetSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Dataset.objects.all()
        return Dataset.objects.filter(workspace__user=self.request.user)
