
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

# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')

# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

@api_view()
def hello_world(request):
    return Response({ "data": {"message": "Hello, world!"}})

# Routers provide an easy way of automatically determining the URL conf.
api_router = routers.DefaultRouter()
api_router.register(r'users', UserViewSet)

app_name = 'api'
urlpatterns = [

#    url(r'^v1/', include((api_router.urls, 'api'))),
    url(r'hello/$', hello_world),

]

