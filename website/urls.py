
# The `urlpatterns` list routes URLs to views. For more information please see:
# https://docs.djangoproject.com/en/2.1/topics/http/urls/

from django.contrib import admin
from django.urls import include, path
from django.conf.urls import url, include

from api.urls import api_router

urlpatterns = [

    path('api/v1/', include('api.urls')),
    path('api/v1/', include(api_router.urls)),

    path('polls/', include('polls.urls')),
    path('admin/', admin.site.urls),
]
