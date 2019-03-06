import os

from django.urls import path
from rest_framework import routers, urls
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

import analitico.utilities
import api.views


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
router.register("endpoints", api.views.EndpointViewSet, basename="endpoint")  # inference delivery endpoint
router.register("logs", api.views.LogViewSet, basename="log")  # log plugins
router.register("jobs", api.views.JobViewSet, basename="job")  # sync and async job running
router.register("models", api.views.ModelViewSet, basename="model")  # trained machine learning models
router.register("recipes", api.views.RecipeViewSet, basename="recipe")  # machine learning algorightms
router.register("tokens", api.views.TokenViewSet, basename="token")  # handles access
router.register("users", api.views.UserViewSet, basename="user")  # user profiles
router.register("workspaces", api.views.WorkspaceViewSet, basename="workspace")  # provides grouping
router.register("plugins", api.views.PluginViewSet, basename="plugin")  # extension plugins

urlpatterns = router.urls + [path("runtime", runtime)]
