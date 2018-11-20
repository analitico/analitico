
from django.contrib import admin
from django.urls import include, path
from django.conf.urls import url, include
from django.contrib.auth.models import User

from rest_framework import routers, serializers, viewsets
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view

from . import views

from .views import UserViewSet, hello_world

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)


app_name = 'api'
urlpatterns = [
    url(r'v1/', include(router.urls)),
    url(r'v1/hello-world/$', hello_world),
]

