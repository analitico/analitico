
from django.shortcuts import render

from rest_framework import routers, serializers, viewsets
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view

from api.models import User
from api.utilities import api_wrapper, api_handle_inference



# Serializers define the API representation.
#class UserSerializer(serializers.HyperlinkedModelSerializer):
#    class Meta:
#        model = User2
#        fields = ('url', 'username', 'email', 'is_staff')

# ViewSets define the view behavior.
#class UserViewSet(viewsets.ModelViewSet):
#    queryset = User.objects.all()
#    serializer_class = UserSerializer

@api_view()
def hello(request):
    return Response({ "data": {"message": "Hello, analitico"}})

##
## supermercato24.it
##

import s24.ordersorting
import s24.ordertime

# cached model used to predict order times
ordertime_model = None

@api_view(['GET', 'POST'])
def s24_order_sorting(request: Request) -> Response:
    return api_wrapper(s24.ordersorting.handle_request, request)

@api_view(['GET', 'POST'])
def s24_order_time(request: Request) -> Response:
    global ordertime_model
    if (ordertime_model is None):
        ordertime_model = s24.ordertime.OrderTimeModel()
    return  api_handle_inference(ordertime_model, request)
