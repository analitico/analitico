"""
Views and ViewSets for API models
"""

import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated

import api.models
import api.utilities

from analitico import ACTION_PROCESS
from api.models import Dataset, Job, ASSETS_CLASS_DATA

from .itemviewsetmixin import ItemViewSetMixin, filterset, ITEM_SEARCH_FIELDS, ITEM_FILTERSET_FIELDS
from .attributeserializermixin import AttributeSerializerMixin
from .filesviewsetmixin import FilesViewSetMixin
from .jobviews import JobViewSetMixin
from .notebookviews import NotebookViewSetMixin
from .k8viewsetmixin import K8ViewSetMixin

##
## DatasetSerializer
##


class DatasetSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Dataset model """

    class Meta:
        model = Dataset
        exclude = ("attributes",)

    notebook = serializers.JSONField(required=False, allow_null=True)


##
## DatasetViewSet - list, detail, post and update datasets
##


class DatasetViewSet(
    ItemViewSetMixin, FilesViewSetMixin, JobViewSetMixin, NotebookViewSetMixin, K8ViewSetMixin, rest_framework.viewsets.ModelViewSet
):
    """
    A dataset model is used to store information on a dataset which is a plugin
    or collection of plugins that can extract, transform and load (ETL) a data source
    and produce clean data which is then used for example to train a model. A dataset
    exposes the same endpoints as all other models + specific endpoints to load
    and deal with file assets.
    """

    item_class = api.models.Dataset
    serializer_class = DatasetSerializer
    job_actions = (ACTION_PROCESS,)

    ordering = ("-updated_at",)
    search_fields = ITEM_SEARCH_FIELDS  # defaults
    filterset_fields = ITEM_FILTERSET_FIELDS  # defaults

    # Views that are used to see records in csv and parquet
    # files can be found in the assets/files mixin
