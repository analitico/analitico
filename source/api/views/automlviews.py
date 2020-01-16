import requests
import json
from django.http import HttpResponse

import rest_framework
from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from analitico import AnaliticoException

from api.models import Model, Automl
from api.views.modelviews import ModelSerializer
from api.kubeflow import (
    automl_run,
    automl_convert_request_for_prediction,
    automl_model_schema,
    automl_model_statistics,
    automl_model_examples,
)
from api.k8 import k8_normalize_name

from .attributeserializermixin import AttributeSerializerMixin
from .itemviewsetmixin import ItemViewSetMixin, filterset, ITEM_SEARCH_FIELDS, ITEM_FILTERSET_FIELDS
from .filesviewsetmixin import FilesViewSetMixin
from .k8viewsetmixin import K8ViewSetMixin
from .kubeflowviewsetmixin import KubeflowViewSetMixin


class AutomlSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Automl model """

    class Meta:
        model = Automl
        exclude = ("attributes",)


##
## AutomlViewSet - list, detail, post, update
##


class AutomlViewSet(
    ItemViewSetMixin, FilesViewSetMixin, K8ViewSetMixin, KubeflowViewSetMixin, rest_framework.viewsets.ModelViewSet
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

    @action(methods=["POST"], detail=True, url_name="predict", url_path="predict")
    def predict(self, request, pk):
        """ Convert Tensorflow prediction request from json format to base64 json format and
        send the request to the item's endpoint. Return the response from the prediction.  """
        item = self.get_object()

        # eg: { "instances": [ {"sepal_length":6.4, "sepal_width":2.8, "petal_length":5.6, "petal_width":2.2} ] }
        content = request.data

        json_request = automl_convert_request_for_prediction(item, content)

        if not json_request:
            raise AnaliticoException(
                "Model schema not found. Has the item's automl config been run?", status_code=status.HTTP_404_NOT_FOUND
            )

        url = f"https://{k8_normalize_name(item.workspace.id)}-tfserving.cloud.analitico.ai/v1/models/{item.id}:predict"
        response = requests.post(url, json_request)

        return HttpResponse(
            response.content, status=response.status_code, content_type=response.headers.get("content-type")
        )

    @action(methods=["GET"], detail=True, url_name="schema", url_path="schema")
    def model_schema(self, request, pk):
        """ Return the recipe's model schema """
        item = self.get_object()

        schema_json = automl_model_schema(item, to_json=True)

        if not schema_json:
            raise AnaliticoException(
                "Model schema not found. Has the item's automl config been run?", status_code=status.HTTP_404_NOT_FOUND
            )

        return Response(json.loads(schema_json), status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["GET"], detail=True, url_name="statistics", url_path="statistics")
    def model_statistics(self, request, pk):
        """ Return the recipe's dataset statistics """
        item = self.get_object()

        stats_json = automl_model_statistics(item, to_json=True)

        if not stats_json:
            raise AnaliticoException(
                "TensorFlow Extended statistics not found. Has the item's automl config been run?",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return Response(json.loads(stats_json), status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["GET"], detail=True, url_name="examples", url_path="examples")
    def model_examples(self, request, pk):
        """ Return a set of random examples from the eval dataset """
        item = self.get_object()

        quantity = 10
        examples, labels = automl_model_examples(item, quantity=quantity, to_json=True)

        if not examples:
            raise AnaliticoException(
                "Model examples not found. Has the item's automl config been run?",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        data = f'{{ "instances": {examples}, "labels": {labels} }}'

        return Response(json.loads(data), status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["POST"], detail=True, url_name="run", url_path="automl")
    def run(self, request, pk):
        """ Execute an Automl configuration specified in the item """
        item = self.get_object()

        model = automl_run(item, serving_endpoint=True)

        serializer = ModelSerializer(model)
        return Response(serializer.data)
