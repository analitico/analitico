from django.shortcuts import render
from django.contrib.auth.models import User

from rest_framework import routers, serializers, viewsets
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view

from analitico.api import api_wrapper
from s24.sorting import handle_sorting_request


@api_view(['GET', 'POST'])
def order_sorting(request):
    return api_wrapper(handle_sorting_request, request)
