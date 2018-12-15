
# TokenSerializer and TokenViewSet for token APIs
# pylint: disable=no-member

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Project

# Django ViewSet
# https://www.django-rest-framework.org/api-guide/viewsets/

# Django Serializers
# https://www.django-rest-framework.org/api-guide/serializers/

class ProjectSerializer(serializers.ModelSerializer):
    """ Serializer for API authorization tokens. """

    class Meta:
        model = Project
        fields = ('id', 'settings', 'notes', 'created_at')

    settings = serializers.JSONField(help_text=_('Project settings including metadata, model type, training parameters, etc...'), required=False)


class ProjectViewSet(viewsets.ModelViewSet):
    """ 
    List, detail, create, update and delete API auth tokens. 
    
    retrieve: Retrieve a specific API auth token.
    list: Retrieve a list of API auth tokens for the user.
    create: Create a new API auth token for the user.
    update: Modify a previously created API auth token (eg: change its name).
    partial_update: Modify a previously created API auth token (eg: change its name).
    delete: Delete an API auth token.
    """
    
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    help_text='help text viewset'
    label ='viewset label'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(user=self.request.user)

    def create(self, request):
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            token = Project(pk=serializer.validated_data['id'])
            if 'name' in serializer.validated_data:
                token.name = serializer.validated_data['name']
            token.user = request.user
            token.save()
            serializer = ProjectSerializer(token)
            return Response(serializer.data, status=201)
        raise exceptions.ValidationError(serializer.errors)
