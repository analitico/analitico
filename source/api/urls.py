
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
from .views import UserViewSet, hello, s24_order_time, s24_order_sorting





# Routers provide an easy way of automatically determining the URL conf.
api_router = routers.DefaultRouter()
api_router.register('users', UserViewSet)

app_name = 'api'
urlpatterns = [

    url('hello/$', hello),

    url('s24/order-sorting', s24_order_sorting),
    url('s24/order-time', s24_order_time),
]

