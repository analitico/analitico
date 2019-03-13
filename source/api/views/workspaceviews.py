"""
Views and ViewSets for API models
"""

import rest_framework
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

import api.models
import api.utilities
from analitico.utilities import logger, get_dict_dot
from api.models import Workspace, Dataset

from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .logviews import LogViewSetMixin

##
## WorkspaceSerializer
##


class WorkspaceSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Workspace model """

    class Meta:
        model = Workspace
        exclude = ("attributes",)

    user = serializers.EmailField(source="user.email", required=False)
    group = serializers.CharField(source="group.name", required=False)

    def create(self, validated_data, *args, **kwargs):
        """ Creates a workspace and assigns it to the currently authenticated user and the requested group (if any) """
        groupname = get_dict_dot(validated_data, "group.name")
        if "user" in validated_data:
            validated_data.pop("user")  # ignore and use authenticated user instead
        if "group" in validated_data:
            validated_data.pop("group")  # pop and check if user belongs to group

        workspace = Workspace(**validated_data)
        workspace.user = self.context["request"].user

        if groupname:
            try:
                group = workspace.user.groups.get(name=groupname)
                workspace.group = group
            except ObjectDoesNotExist:
                message = "Group does not exist or the user does not belong to the group."
                raise serializers.ValidationError({"group": message})
                # TODO figure out why the payload in the exception above is flattened when the error is reported
                # raise exceptions.ValidationError(_('The specified group does not exist or the user does not belong to the group.'))
        workspace.save()
        return workspace

    def update(self, instance, validated_data):
        """ Update item even partially and with unknown 'attributes' keys. """
        # 'id' is immutable
        # 'type' is immutable
        # TODO should 'user' and 'group' be updateable?
        if "id" in validated_data:
            instance.id = validated_data["id"]
        if "title" in validated_data:
            instance.title = validated_data["title"]
        if "description" in validated_data:
            instance.description = validated_data["description"]
        if "attributes" in validated_data:
            for (key, value) in validated_data["attributes"].items():
                # TODO we should consider validating attributes against a fixed schema
                instance.set_attribute(key, value)
        instance.save()
        return instance


##
## WorkspaceViewSet - list, detail, post and update workspaces
## pylint: disable=no-member


class WorkspaceViewSet(AssetViewSetMixin, LogViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ 
    List, detail, create, update and delete machine learning project trainings

    retrieve: Retrieve a specific project.
    list: Retrieve a list of projects for the user.
    create: Create a new project for the user.
    update: Update a previously created project.
    partial_update: Modify a previously created project.
    delete: Delete a project.
    """

    item_class = api.models.Workspace
    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            if self.request.user.is_superuser:
                return Workspace.objects.all()
            return Workspace.objects.filter(user=self.request.user)
        return Workspace.objects.none()
