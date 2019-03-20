import rest_framework
import json

from django.http import HttpResponse

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated

import api.models
import api.utilities

from analitico import ACTION_PROCESS
from api.models import Notebook, NOTEBOOK_MIME_TYPE

from api.models.notebook import nb_convert_to_html

from .itemviewsetmixin import ItemViewSetMixin
from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .jobviews import JobViewSetMixin
from .logviews import LogViewSetMixin

##
## NotebookSerializer
##


class NotebookSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for notebook model """

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
        response = HttpResponse(content=content, content_type=NOTEBOOK_MIME_TYPE)
        return response

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="detail-html", url_path="html")
    def html(self, request, pk):
        """ Returns the notebook content converted to html, accepts ?template parameter for 'basic' or 'full' templates """
        item = self.get_object()
        if not item.notebook:
            raise NotFound("Notebook model " + self.id + " does not contain an actual Jupyter notebook yet.")
        template = api.utilities.get_query_parameter(request, "template", "full")
        content, _ = nb_convert_to_html(item.notebook, template)
        return HttpResponse(content=content, content_type="text/html")

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="process", url_path="process")
    def data_process(self, request, pk):
        return self.job_create(request, pk, ACTION_PROCESS)
