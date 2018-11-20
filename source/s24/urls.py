
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
from .views import order_sorting

# Routers provide an easy way of automatically determining the URL conf.
#api_router = routers.DefaultRouter()
#api_router.register('users', UserViewSet)

app_name = 's24'
urlpatterns = [

    url('order-sorting', order_sorting),

]

