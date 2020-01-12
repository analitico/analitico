import requests
import json
from django.http import HttpResponse

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from api.views.modelviews import ModelSerializer

from api.kubeflow import (
    automl_run,
    automl_convert_request_for_prediction,
    automl_model_schema,
    automl_model_statistics,
    automl_model_examples,
)
from api.k8 import k8_normalize_name


class AutomlViewSetMixin:

    # All methods require prior authentication, no token, no access
    permission_classes = (IsAuthenticated,)

    @action(methods=["POST"], detail=True, url_name="automl-predict", url_path="automl/predict")
    def predict(self, request, pk):
        """ Convert Tensorflow prediction request from json format to base64 json format and
        send the request to the item's endpoint. Return the response from the prediction.  """
        item = self.get_object()

        # eg: { "instances": [ {"sepal_length":6.4, "sepal_width":2.8, "petal_length":5.6, "petal_width":2.2} ] }
        content = request.data

        json_request = automl_convert_request_for_prediction(item, content)

        url = f"https://{k8_normalize_name(item.workspace.id)}-tfserving.cloud.analitico.ai/v1/models/{item.id}:predict"
        response = requests.post(url, json_request)

        return HttpResponse(
            response.content, status=response.status_code, content_type=response.headers.get("content-type")
        )

    @action(methods=["GET"], detail=True, url_name="automl-schema", url_path="automl/schema")
    def model_schema(self, request, pk):
        """ Return the recipe's model schema """
        item = self.get_object()

        schema_json = automl_model_schema(item, to_json=True)

        return Response(json.loads(schema_json), status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["GET"], detail=True, url_name="automl-statistics", url_path="automl/statistics")
    def model_statistics(self, request, pk):
        """ Return the recipe's dataset statistics """
        item = self.get_object()

        stats_json = automl_model_statistics(item, to_json=True)

        return Response(json.loads(stats_json), status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["GET"], detail=True, url_name="automl-examples", url_path="automl/examples")
    def model_examples(self, request, pk):
        """ Return a set of random examples from the eval dataset """
        item = self.get_object()

        quantity = 10
        examples, labels = automl_model_examples(item, quantity=quantity, to_json=True)

        data = f'{{ "instances": {examples}, "labels": {labels} }}'

        return Response(json.loads(data), status=status.HTTP_200_OK, content_type="application/json")

    @action(methods=["POST"], detail=True, url_name="automl-run", url_path="automl")
    def run(self, request, pk):
        """ Execute an Automl configuration specified in the item """
        item = self.get_object()

        model = automl_run(item, serving_endpoint=True)

        serializer = ModelSerializer(model)
        return Response(serializer.data)
