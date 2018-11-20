"""prova001 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from django.conf.urls import url, include
from django.contrib.auth.models import User

from rest_framework import routers, serializers, viewsets
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view



# Routers provide an easy way of automatically determining the URL conf.
#router = routers.DefaultRouter()

from api.urls import UserViewSet, hello_world, api_router

#router.register(r'users', UserViewSet)


urlpatterns = [
#    url(r'api/v1/hello-world/$', hello_world),

 #   url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    path(r'api/v1/', include('api.urls')),
    path(r'api/v1/', include(api_router.urls)),

    path('polls/', include('polls.urls')),
    path('admin/', admin.site.urls),
]
