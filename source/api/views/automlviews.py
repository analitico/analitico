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
from api.views.modelviews import ModelSerializer
from api.kubeflow import *
from api.k8 import k8_normalize_name
from api.utilities import get_query_parameter, get_signed_secret

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

        # url points to Kubernetes in-cluster DNS
        url = f"http://{k8_normalize_name(item.workspace.id)}-tfserving.cloud.svc/v1/models/{item.id}:predict"
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

        return Response({"data": json.loads(schema_json)}, status=status.HTTP_200_OK, content_type="application/json")

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

        return Response({"data": json.loads(stats_json)}, status=status.HTTP_200_OK, content_type="application/json")

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

        return Response({"data": json.loads(data)}, status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["GET"], detail=True, url_name="preconditioner", url_path="preconditioner")
    def model_preconditioner_statistics(self, request, pk):
        """ Return statistics generated by the preconditioner component in the automl pipeline """
        item = self.get_object()

        data = automl_model_preconditioner_statistics(item, to_json=True)

        if not data:
            raise AnaliticoException(
                "Model preconditioner not found. Has the item's automl config been run?",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return Response({"data": json.loads(data)}, status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["POST"], detail=True, url_name="run", url_path="automl")
    def run(self, request, pk):
        """ Execute an Automl configuration specified in the item """
        item = self.get_object()

        run = automl_run(item)

        return Response({"data": run}, status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["POST"], detail=True, url_name="serving", url_path="serving", permission_classes=[AllowAny])
    def serving_deploy(self, request, pk):
        """ Deploy the endpoint to serve the recipe's automl model """
        token = get_query_parameter(request, "state", None)
        if token != get_signed_secret(pk):
            raise AnaliticoException("Request unauthorized", status_code=status.HTTP_401_UNAUTHORIZED)

        item = Automl.objects.get(pk=pk)
        if not item:
            raise AnaliticoException("Item not found", status_code=status.HTTP_404_NOT_FOUND)
        
        run_id = item.get_attribute("automl.run_id")
        model = Model.objects.get(attributes__icontains=f'"run_id":"{run_id}"')
        assert model

        tensorflow_serving_deploy(item, model, stage=K8_STAGE_PRODUCTION)

        serializer = ModelSerializer(model)
        return Response(serializer.data)
