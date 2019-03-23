import rest_framework
import json

from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, StaticHTMLRenderer, BrowsableAPIRenderer

import api.models
import api.utilities

from analitico import ACTION_PROCESS
from api.models import Notebook, NOTEBOOK_MIME_TYPE
from api.renderers import NotebookRenderer

from api.models.notebook import nb_convert_to_html, nb_filter_tags
from api.utilities import get_query_parameter, get_query_parameter_as_bool

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
## NotebookViewSetMixin - endpoints for creating jobs attached to an item, eg: train a model
##


class NotebookViewSetMixin:
    """ Provides APIs to operate on Jupyter notebooks contained in the model. """

    def get_notebook_response(self, name, format, template, tags):
        item = self.get_object()
        notebook = item.get_notebook(name)

        if tags:
            notebook = nb_filter_tags(notebook, tags)

        if format == "text/html":
            if not notebook:
                raise NotFound("Notebook model " + item.id + " does not contain the requested Jupyter notebook yet.")
            content, _ = nb_convert_to_html(notebook, template)
            return Response(content, content_type="text/html")
        return Response(notebook)

    @action(
        methods=["get", "put", "post", "patch"],
        detail=True,
        url_name="detail-notebook",
        url_path="notebook",
        renderer_classes=(JSONRenderer, NotebookRenderer, StaticHTMLRenderer, BrowsableAPIRenderer),
        permission_classes=(IsAuthenticated,),
    )
    def notebook(self, request, pk):
        """ Returns the notebook content as is or converted to html with given template """
        name = api.utilities.get_query_parameter(request, "name", "notebook")
        template = api.utilities.get_query_parameter(request, "template", "full")
        format = request.accepted_renderer.media_type
        tags = api.utilities.get_query_parameter(request, "tags", None)

        if request.method in ("POST", "PUT", "PATCH"):
            # replace existing notebook with given notebook
            item = self.get_object()
            old_notebook = item.get_notebook(name)
            notebook = request.data["data"]
            assert "data" in request.data  # serializer adds json:api style "data": xxx
            item.set_notebook(notebook, name)
            item.save()
            # https://restfulapi.net/http-methods/
            return Response(status=status.HTTP_200_OK if old_notebook else status.HTTP_201_CREATED)
        return self.get_notebook_response(name, format, template, tags)


##
## NotebookViewSet - list, detail, edit, post and run notebooks
##


class NotebookViewSet(
    ItemViewSetMixin,
    AssetViewSetMixin,
    JobViewSetMixin,
    LogViewSetMixin,
    NotebookViewSetMixin,
    rest_framework.viewsets.ModelViewSet,
):
    """ An editable and runnable Jupyter notebook and its artifacts """

    item_class = api.models.Notebook
    serializer_class = NotebookSerializer
    job_actions = (ACTION_PROCESS,)

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="process", url_path="process")
    def data_process(self, request, pk):
        tags
        return self.job_create(request, pk, ACTION_PROCESS)
