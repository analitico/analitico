
# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import collections

from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist

import rest_framework
from rest_framework import serializers
from rest_framework import exceptions
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError

from api.models import ModelMixin, Workspace, Dataset, Recipe
from analitico.utilities import logger, get_dict_dot
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
# ItemSerializer
#
# Item is a generic model which is used to store different kinds of objects. All of them
# have a few fields in common while the rest of the payload is stored in 'json', a dictionary.
# This allows easy extension without having to refactor the SQL storage continuosly and introduce
# new migrations and releases. Also different versions can coexist and ignore extra data.
#

class SerializerMixin():

    def to_representation(self, obj):
        """ Serialize object to dictionary, extracts all json key to main level """
        data = super().to_representation(obj)
        reformatted = {
            'type': obj.type,
            'id': data.pop('id'),
            'attributes': data
        }
        if obj.attributes:
            for key in obj.attributes:
                data[key] = obj.attributes[key]
        return reformatted


    def to_internal_value(self, data):        
        """ Convert dictionary to internal representation (all unknown fields go into json) """

        # works with input in json:api style (attributes) or flat json
        attributes = data.pop('attributes') if 'attributes' in data else data.copy()

        for (key, _) in self.fields.fields.items():
            if key in attributes:
                data[key] = attributes.pop(key)

        # Perform the data validation, eg:
        # if not blabla:
        #    raise serializers.ValidationError({
        #        'blabla': 'This field is required.'
        #    })

        # Use regular serializer for everything but the json contents which go as-is
        validated = super().to_internal_value(data)
        validated['attributes'] = attributes

        # Return the validated values which will be available as `.validated_data`.
        return validated

##
## WorkspaceSerializer
##

class WorkspaceSerializer(SerializerMixin, serializers.ModelSerializer):
    """ Serializer for Workspace model """

    class Meta:
        model = Workspace
        exclude = ('attributes', )

    user = serializers.EmailField(source='user.email', required=False)
    group = serializers.CharField(source='group.name', required=False)

    def create(self, validated_data, *args, **kwargs):
        """ Creates a workspace and assigns it to the currently authenticated user and the requested group (if any) """

        groupname = get_dict_dot(validated_data, 'group.name')
        validated_data.pop('user') # ignore and use authenticated user instead
        validated_data.pop('group') # pop and check if user belongs to group

        workspace = Workspace(**validated_data)
        workspace.user = self.context['request'].user

        try:
            group = workspace.user.groups.get(name=groupname)
            workspace.group = group
        except ObjectDoesNotExist:
            raise serializers.ValidationError({
                'group': _('The specified group does not exist or the user does not belong to the group.')
            })
            # TODO figure out why the payload in the exception above is flattened when the error is reported
            # raise exceptions.ValidationError(_('The specified group does not exist or the user does not belong to the group.'))

        workspace.save()
        return workspace


##
## DatasetSerializer
##

class DatasetSerializer(serializers.ModelSerializer, SerializerMixin):
    """ Serializer for Dataset model """

    class Meta:
        model = Dataset
        exclude = ('attributes', )



#
# ViewSetMixin - shared features
#

class ViewSetMixin():
    pass


##
## WorkspaceViewSet - list, detail, post and update workspaces
## 

class WorkspaceViewSet(ViewSetMixin, viewsets.ModelViewSet):
    """ 
    List, detail, create, update and delete machine learning project trainings. 
    
    retrieve: Retrieve a specific project.
    list: Retrieve a list of projects for the user.
    create: Create a new project for the user.
    update: Update a previously created project.
    partial_update: Modify a previously created project.
    delete: Delete a project.
    """

    item_class = Workspace
    serializer_class = WorkspaceSerializer

    help_text='help text viewset'
    label ='viewset label'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Workspace.objects.all()
        return Workspace.objects.filter(workspace__user=self.request.user)



##
## DatasetViewSet - list, detail, post and update datasets
##

class DatasetViewSet(ViewSetMixin, viewsets.ModelViewSet):

    item_class = Dataset
    serializer_class = DatasetSerializer

    def get_queryset(self):
        return Dataset.objects.all()
        #if self.request.user.is_superuser:
        #    return Dataset.objects.all()
        #return Dataset.objects.filter(workspace__user=self.request.user)

