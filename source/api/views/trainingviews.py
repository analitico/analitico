
# TrainingSerializer and TrainingViewSet for training APIs
# pylint: disable=no-member

from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist

import rest_framework
from rest_framework import serializers
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError

from api.models import Project, Training
from analitico.utilities import logger
from api.utilities import time_ms, api_get_parameter, api_check_authorization

import analitico.models
import analitico.utilities
import analitico.storage

import api.models
import api.utilities

# Django Serializers
# https://www.django-rest-framework.org/api-guide/serializers/

# Django ViewSet
# https://www.django-rest-framework.org/api-guide/viewsets/

#
# Serializer
#

class TrainingSerializer(serializers.ModelSerializer):
    """ Serializer for machine learning project training set. """

    class Meta:
        model = Training
        fields = ('id', 'status', 'settings', 'results', 'notes', 'created_at', 'updated_at')

    id = serializers.SlugField(help_text=_("Unique id."))
#    user = serializers.EmailField(source='owner.email', help_text=_('User that owns the project.'), required=False)
#    group = serializers.CharField(source='group.name', help_text=_('Project notes (markdown)'), required=False)

    status = serializers.CharField(help_text=_('Training status'), required=False)
    settings = serializers.JSONField(help_text=_('Project settings'), required=False)
    results = serializers.JSONField(help_text=_('Training results'), required=False)
    notes = serializers.CharField(help_text=_('Training notes (markdown)'), required=False)

    created_at = serializers.DateTimeField(label=_('Created'), help_text=_('Date and time when project was created.'), required=False)
    updated_at = serializers.DateTimeField(label=_('Updated'), help_text=_('Date and time when project was last updated.'), required=False)


#
# ViewSet
#

class TrainingViewSet(rest_framework.viewsets.ModelViewSet):
    """ 
    List, detail, create, update and delete machine learning project trainings. 
    
    retrieve: Retrieve a specific project.
    list: Retrieve a list of projects for the user.
    create: Create a new project for the user.
    update: Update a previously created project.
    partial_update: Modify a previously created project.
    delete: Delete a project.
    """
    
    serializer_class = TrainingSerializer
    permission_classes = [IsAuthenticated]

    help_text='help text viewset'
    label ='viewset label'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Training.objects.all()
        return Project.objects.filter(owner=self.request.user)


    def create(self, request, *args, **kwargs):
        serializer = TrainingSerializer(data=request.data)
        if serializer.is_valid():
            token = Training(pk=serializer.validated_data['id'])
            if 'name' in serializer.validated_data:
                token.name = serializer.validated_data['name']
            token.user = request.user
            token.save()
            serializer = TrainingSerializer(token)
            return Response(serializer.data, status=201)
        raise exceptions.ValidationError(serializer.errors)
