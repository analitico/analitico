import os

from django.urls import path
from rest_framework import routers

import api.views


app_name = "api"

description_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "description.md")
with open(description_filename) as f:
    description = f.read()

# Routers provide an easy way of automatically determining the URL conf.
router = routers.SimpleRouter(trailing_slash=False)

router.register("tokens", api.views.TokenViewSet, basename="token")  # handles access
router.register("workspaces", api.views.WorkspaceViewSet, basename="workspace")  # provides grouping
router.register("datasets", api.views.DatasetViewSet, basename="dataset")  # extract, transform, load pipeline
router.register("recipes", api.views.RecipeViewSet, basename="recipe")  # machine learning algorightms
router.register("jobs", api.views.JobViewSet, basename="job")  # sync and async job running
router.register("models", api.views.ModelViewSet, basename="model")  # trained machine learning models
router.register("endpoints", api.views.EndpointViewSet, basename="endpoint")  # inference delivery endpoint

# deprecated, to be removed soon
router.register("projects", api.views.ProjectViewSet, basename="project")
router.register("trainings", api.views.TrainingViewSet, basename="training")

urlpatterns = router.urls + [
    path("project/<str:project_id>/training", api.views.handle_prj_training),
    #   path('project/<str:project_id>/inference', api.views.handle_prj_inference),
    path("project/<str:project_id>/upload/<str:path>", api.views.handle_prj_upload),
    path("training/<str:training_id>", api.views.handle_trn),
    path("training/<str:training_id>/activate", api.views.handle_trn_activate),
]
