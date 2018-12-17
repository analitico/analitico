
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
    """ Serializer for machine learning projects. """

    class Meta:
        model = Project
        fields = ('id', 'user', 'group', 'settings', 'training_id', 'notes', 'created_at', 'updated_at')

    id = serializers.SlugField(help_text=_("Unique id."))
    user = serializers.EmailField(source='owner.email', help_text=_('User that owns the project.'), required=False)
    group = serializers.CharField(source='group.name', help_text=_('Project notes (markdown)'), required=False)

    settings = serializers.JSONField(help_text=_('Project settings including metadata, model type, training parameters, etc...'), required=False)
    training_id = serializers.SlugField(help_text=_("Training session currently used for inference."), required=False)
    notes = serializers.CharField(help_text=_('Project notes (markdown)'), required=False)

    created_at = serializers.DateTimeField(label=_('Created'), help_text=_('Date and time when project was created.'), required=False)
    updated_at = serializers.DateTimeField(label=_('Updated'), help_text=_('Date and time when project was last updated.'), required=False)



class ProjectViewSet(viewsets.ModelViewSet):
    """ 
    List, detail, create, update and delete machine learning projects. 
    
    retrieve: Retrieve a specific project.
    list: Retrieve a list of projects for the user.
    create: Create a new project for the user.
    update: Update a previously created project.
    partial_update: Modify a previously created project.
    delete: Delete a project.
    """
    
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    help_text='help text viewset'
    label ='viewset label'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(owner=self.request.user)

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
