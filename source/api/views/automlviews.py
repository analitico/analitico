import requests
import json
from django.http import HttpResponse

import rest_framework
from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from analitico import AnaliticoException

from api.models import Model, Automl
from api.factory import factory
from api.views.modelviews import ModelSerializer
from api.k8 import k8_normalize_name
from api.utilities import get_query_parameter, get_signed_secret
from api.permissions import has_item_permission_or_exception

from .attributeserializermixin import AttributeSerializerMixin
from .itemviewsetmixin import ItemViewSetMixin, filterset, ITEM_SEARCH_FIELDS, ITEM_FILTERSET_FIELDS
from .filesviewsetmixin import FilesViewSetMixin
from .k8viewsetmixin import K8ViewSetMixin
from .jobviews import JobViewSetMixin


class AutomlSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Automl model """

    class Meta:
        model = Automl
        exclude = ("attributes",)


##
## AutomlViewSet - list, detail, post, update
##


class AutomlViewSet(
    ItemViewSetMixin, FilesViewSetMixin, JobViewSetMixin, K8ViewSetMixin, rest_framework.viewsets.ModelViewSet
):
    """
    An Automl object describes the configuration for generating a model
    through the execution of a machine learning pipeline.
    """

    item_class = Automl
    serializer_class = AutomlSerializer

    ordering = ("-updated_at",)
    search_fields = ITEM_SEARCH_FIELDS  # defaults
    filterset_fields = ITEM_FILTERSET_FIELDS  # defaults