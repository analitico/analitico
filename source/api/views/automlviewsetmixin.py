from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.views.modelviews import ModelSerializer

from api.kubeflow import automl_run


class AutomlViewSetMixin:
    """ """

    @action(methods=["POST"], detail=True, url_name="automl-run", url_path="automl")
    def run(self, request, pk):
        item = self.get_object()

        model = automl_run(item)

        serializer = ModelSerializer(model)
        return Response(serializer.data)