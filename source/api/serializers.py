
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

from api.models import AttributesMixin, Workspace, Dataset, Recipe
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

        # If this payload is in json:api format it will have a 'data'
        # element which contains the actual payload. If in json format
        # it will just have a regular dictionary with the data directly in it
        if 'data' in data:
            data = data['data']

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
        
        if 'user' in validated_data: validated_data.pop('user') # ignore and use authenticated user instead
        if 'group' in validated_data: validated_data.pop('group') # pop and check if user belongs to group

        workspace = Workspace(**validated_data)
        workspace.user = self.context['request'].user

        if groupname:
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


    def update(self, instance, validated_data):
        """ Update item even partially and with unknown 'attributes' keys. """

        # 'id' is immutable
        # 'type' is immutable
        # TODO should 'user' and 'group' be updateable?

        if 'id' in validated_data:
            instance.id = validated_data['id']
        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'description' in validated_data:
            instance.description = validated_data['description']
        if 'attributes' in validated_data:
            for (key, value) in validated_data['attributes'].items():
                # TODO we should consider validating attributes against a fixed schema
                instance.set_attribute(key, value)

        instance.save()
        return instance


##
## DatasetSerializer
##

class DatasetSerializer(SerializerMixin, serializers.ModelSerializer):
    """ Serializer for Dataset model """

    class Meta:
        model = Dataset
        exclude = ('attributes', )


