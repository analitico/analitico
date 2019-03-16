import rest_framework
import json

from django.http import HttpResponse
from django.views.decorators.http import etag

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

import api.models
import api.utilities

from analitico import ACTION_PROCESS
from api.models import Dataset, Job, ASSETS_CLASS_DATA, Notebook

from .itemviewsetmixin import ItemViewSetMixin
from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .jobviews import JobViewSetMixin
from .logviews import LogViewSetMixin

##
## NotebookSerializer
##


class NotebookSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Dataset model """

    class Meta:
        model = Notebook
        exclude = ("attributes",)

    notebook = serializers.JSONField()


##
## NotebookViewSet - list, detail, edit, post and run notebooks
##


class NotebookViewSet(
    ItemViewSetMixin, AssetViewSetMixin, JobViewSetMixin, LogViewSetMixin, rest_framework.viewsets.ModelViewSet
):
    """ An editable and runnable Jupyter notebook and its artifacts """

    item_class = api.models.Notebook
    serializer_class = NotebookSerializer
    job_actions = (ACTION_PROCESS,)

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="detail-notebook", url_path="notebook")
    def notebook(self, request, pk):
        """ Returns the notebook content """
        item = self.get_object()
        content = json.dumps(item.notebook, indent=4) if item.notebook else ""
        response = HttpResponse(content=content, content_type="application/json")
        return response

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="process", url_path="process")
    def data_process(self, request, pk):
        return self.job_create(request, pk, ACTION_PROCESS)
