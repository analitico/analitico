from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.request import Request

from api.views.modelviews import ModelSerializer
from api.utilities import get_query_parameter

import api.kubeflow
from api.kubeflow import *


class KubeflowViewSetMixin:
    @action(
        methods=["GET"], detail=True, url_name="kf-pipeline-runs", url_path=r"kf/pipeline/runs/(?P<run_id>[-\w.]{0,64})"
    )
    def pipeline_runs(self, request, pk, run_id: str = None):
        item = self.get_object()

        # token used by KFP SDK to get the next page from paginated results
        list_page_token = get_query_parameter(request, "list_page_token", "")

        runs = kf_pipeline_runs_get(item, run_id, list_page_token=list_page_token)

        return Response(runs, content_type="application/json")

    @action(
        methods=["POST"], detail=True, url_name="tfjob-deploy", url_path="kf/tfjob", permission_classes=[IsAdminUser]
    )
    def tensorflow_job(self, request, pk):
        """ 
        Deploy a TensorFlow Job for running a distributed Analitico Automl trainer
        setup with the given configuration. 
        """
        item = self.get_object()

        # TODO: eg, .. trainer config
        config = request.data
        if "data" in config:
            config = config["data"]
        if not config:
            raise AnaliticoException("Please provide a valid trainer configuration", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        tfjob = tensorflow_job_deploy(item, config)

        return Response(tfjob, content_type="application/json")

    @action(
        methods=["GET"],
        detail=True,
        url_name="tfjob-get",
        url_path=r"kf/tfjob/(?P<tfjob_id>[-\w.]{0,64})",
        permission_classes=[IsAdminUser],
    )
    def tensorflow_job_get(self, request, pk, tfjob_id):
        item = self.get_object()

        tfjob = api.kubeflow.tensorflow_job_get(item, tfjob_id)

        return Response(tfjob, content_type="application/json")
