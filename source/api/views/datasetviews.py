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
from .itemviewsetmixin import ItemViewSetMixin
from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .jobviews import JobViewSetMixin
from .logviews import LogViewSetMixin
from .notebookviews import NotebookViewSetMixin

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
    ItemViewSetMixin,
    AssetViewSetMixin,
    JobViewSetMixin,
    LogViewSetMixin,
    NotebookViewSetMixin,
    rest_framework.viewsets.ModelViewSet,
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

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="detail-data-process", url_path="data/process")
    def data_process(self, request, pk):
        return self.job_create(request, pk, ACTION_PROCESS)

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="detail-data-csv", url_path="data/csv")
    def data_csv(self, request, pk):
        return self.asset_detail(request, pk, ASSETS_CLASS_DATA, "data.csv")

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="detail-data-json", url_path="data/json")
    def data_json(self, request, pk):
        """ Returns /data/data.csv as an array of json records with paging support """
        return self.asset_download_csv_as_json_with_paging(request, pk, ASSETS_CLASS_DATA, "data.csv")

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="detail-data-info", url_path="data/info")
    def data_info(self, request, pk):
        return self.asset_detail_info(request, pk, ASSETS_CLASS_DATA, "data.csv")
