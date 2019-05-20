"""
Views and ViewSets for API models
"""

import rest_framework
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

import api.models
import api.utilities

from analitico.utilities import logger, get_dict_dot
from api.models import Workspace, Dataset, Role
from api.permissions import has_item_permission

from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .logviews import LogViewSetMixin

##
## WorkspaceSerializer
##


def comma_separated_to_array(items: str):
    if items and items.strip():
        return [x.strip() for x in items.split(",")]
    return None


class WorkspaceSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Workspace model """

    class Meta:
        model = Workspace
        exclude = ("attributes",)

    user = serializers.EmailField(source="user.email", required=False)
    group = serializers.CharField(source="group.name", required=False)

    def to_representation(self, item):
        """ Serialize object to dictionary, extracts all json key to main level """
        data = super().to_representation(item)

        # workspace has an owner which has all permissions on it and the items it contains.
        # optionally, the owner can invite other users to the workspace and given them access
        # using specific roles and permissions. only the owner or admins can see all the rights.
        # while other users that have been invited only see their own rigths
        # pylint: disable=no-member
        user = self.context["request"].user
        roles = Role.objects.filter(workspace=item)
        if not has_item_permission(user, item, "analitico.workspace.admin"):
            # user has been invited to workspace and only sees his own rights
            roles = roles.filter(user=user)

        data["attributes"]["users"] = {}
        for role in roles.all():
            data["attributes"]["users"][role.user.email] = {
                "roles": comma_separated_to_array(role.roles),
                "permissions": comma_separated_to_array(role.permissions),
            }

        return data

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
