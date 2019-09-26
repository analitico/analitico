"""
Views and ViewSets for API models
"""

import rest_framework

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

import api.models
import api.utilities
import api.notifications

from analitico.utilities import logger, get_dict_dot, comma_separated_to_array, array_to_comma_separated, set_dict_dot
from api.models import Workspace, Dataset, Role, User
from api.permissions import has_item_permission, has_item_permission_or_exception
from api.k8 import k8_deploy_jupyter

from .attributeserializermixin import AttributeSerializerMixin
from .itemviewsetmixin import ItemViewSetMixin
from .filesviewsetmixin import FilesViewSetMixin
from .jobviews import JobViewSetMixin

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
    permissions = serializers.JSONField(required=False)

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
        if not has_item_permission(user, item, "analitico.workspaces.admin"):
            # user has been invited to workspace and only sees his own rights
            roles = roles.filter(user=user)

        data["attributes"]["permissions"] = {}
        for role in roles.all():
            data["attributes"]["permissions"][role.user.email] = {
                "roles": comma_separated_to_array(role.roles),
                "permissions": comma_separated_to_array(role.permissions),
            }

        # add url and html that can be used to enable slack configuration on this workspace
        btn_url, btn_html = api.notifications.slack_get_install_button_url(self.context["request"], item.id)
        set_dict_dot(data, "attributes.slack.button.url", btn_url)
        set_dict_dot(data, "attributes.slack.button.html", btn_html)

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

        # provision storage for this workspace
        if not workspace.get_attribute("storage"):
            api.models.drive.dr_create_workspace_storage(workspace)

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

        # only the owner of the workspace and add or remove users and update their rights
        permissions = validated_data.get("permissions", None)
        if permissions:
            user = self.context["request"].user
            has_item_permission_or_exception(user, instance, "analitico.workspaces.admin")
            # user has been invited to workspace and only sees his own rights
            with transaction.atomic():
                # pylint: disable=no-member
                Role.objects.filter(workspace=instance).delete()
                for key, value in permissions.items():
                    role = Role(workspace=instance, user=User.objects.get(email=key))
                    # TODO could catch here and return a specific exception message if user is unknown
                    role.roles = array_to_comma_separated(value.get("roles", None))
                    role.permissions = array_to_comma_separated(value.get("permissions", None))
                    role.save()

        instance.save()
        return instance


##
## WorkspaceViewSet - list, detail, post and update workspaces
##


class WorkspaceViewSet(ItemViewSetMixin, FilesViewSetMixin, JobViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ Views for workspaces and their access permissions. """

    item_class = api.models.Workspace
    serializer_class = WorkspaceSerializer

    @action(methods=["get"], detail=False, url_name="permissions", url_path="permissions")
    def permissions(self, request):
        """ Returns roles and permissions configurations. """
        return Response(api.permissions.get_configurations())

    @action(methods=["get"], detail=True, url_name="jupyter", url_path="jupyter")
    def jupyter(self, request, pk):
        """ Allocate a Jupyter server if needed, update workspace and return it. """
        workspace = self.get_object()
        k8_deploy_jupyter(workspace)

        serializer = WorkspaceSerializer(workspace, context={"request": request})
        return Response(serializer.data)
