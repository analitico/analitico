import os

from django.urls import path
from rest_framework import routers
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

import analitico.utilities
import api.views
from api.notifications import notifications_webhook

# setup life cycle signal handlers used for example to dispose
# files in storage when a dataset is deleted or remove k8s services
# when a recipe is deleted, etc.
import api.lifecycle

app_name = "api"

description_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "description.md")
with open(description_filename) as f:
    description = f.read()


@api_view()
def runtime(request: Request):
    """ Returns a dictionary of runtime environment """
    runtime = analitico.utilities.get_runtime()
    return Response({"type": "analitico/runtime", **runtime})


# Routers provide an easy way of automatically determining the URL conf.
router = routers.SimpleRouter(trailing_slash=False)

router.register("datasets", api.views.DatasetViewSet, basename="dataset")  # extract, transform, load pipeline
router.register("jobs", api.views.JobViewSet, basename="job")  # sync and async job running
router.register("models", api.views.ModelViewSet, basename="model")  # trained machine learning models
router.register("recipes", api.views.RecipeViewSet, basename="recipe")  # machine learning algorithms
router.register("tokens", api.views.TokenViewSet, basename="token")  # handles access
router.register("users", api.views.UserViewSet, basename="user")  # user profiles
router.register("workspaces", api.views.WorkspaceViewSet, basename="workspace")  # provides grouping
router.register("notebooks", api.views.NotebookViewSet, basename="notebook")  # notebooks
router.register("k8s", api.views.K8ViewSet, basename="k8")  # kubernetes monitoring, operations, etc
router.register("billing", api.views.BillingViewSet, basename="billing")  # billing, plans, invoices, etc...
router.register("automls", api.views.AutomlViewSet, basename="automl")  # machine learning algorithms

urlpatterns = router.urls + [
    path("runtime", runtime, name="runtime"),
    path("notify", notifications_webhook, name="notifications-webhook"),
]
