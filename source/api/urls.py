
import os

from django.urls import path
from rest_framework import routers

import api.views


app_name = 'api'

description_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'description.md')
with open(description_filename) as f:
    description = f.read()

# Routers provide an easy way of automatically determining the URL conf.
router = routers.SimpleRouter()
router.register('projects', api.views.ProjectViewSet, basename='project')
router.register('tokens', api.views.TokenViewSet, basename='token')

urlpatterns = router.urls + [
    
    path('project/<str:project_id>/training', api.views.handle_prj_training),
#   path('project/<str:project_id>/inference', api.views.handle_prj_inference),
    path('project/<str:project_id>/upload/<str:path>', api.views.handle_prj_upload),

    path('training/<str:training_id>', api.views.handle_trn),
    path('training/<str:training_id>/activate', api.views.handle_trn_activate),
]
