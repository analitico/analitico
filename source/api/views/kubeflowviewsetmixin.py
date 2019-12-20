from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.views.modelviews import ModelSerializer
from api.utilities import get_query_parameter

from api.kubeflow import kf_pipeline_runs_get

class KubeflowViewSetMixin:

    @action(methods=["GET"], detail=True, url_name="kf-pipeline-runs", url_path=r"kf/pipeline/runs/(?P<run_id>[-\w.]{0,64})")
    def pipeline_runs(self, request, pk, run_id: str = None):
        item = self.get_object()

        # token used by KFP SDK to get the next page from paginated results
        list_page_token = get_query_parameter(request, "list_page_token", '')

        runs = kf_pipeline_runs_get(item, run_id, list_page_token=list_page_token)

        return Response(runs, content_type="application/json")
