
from django.urls import path
from django.conf.urls import url

from rest_framework.response import Response
from rest_framework.decorators import api_view

import api.views

# Routers provide an easy way of automatically determining the URL conf.
# api_router = routers.DefaultRouter()
# api_router.register('users', UserViewSet)

@api_view(['GET', 'POST'])
def handle_ping(request):
    return Response({ 
        "data": request.data 
    })


app_name = 'api'
urlpatterns = [

    path('ping', handle_ping),

    path('project/<str:project_id>/', api.views.handle_prj),
    path('project/<str:project_id>/training', api.views.handle_prj_training),
    path('project/<str:project_id>/inference', api.views.handle_prj_inference),
    path('project/<str:project_id>/upload/<str:path>', api.views.handle_prj_upload),

    path('training/<str:training_id>', api.views.handle_trn),
    path('training/<str:training_id>/activate', api.views.handle_trn_activate)
]
