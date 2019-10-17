import os
import operator
import functools
import re

from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.request import Request

from analitico import AnaliticoException
from api.models import Workspace, Role, ItemMixin, User
from analitico.utilities import read_json


# preload default list of configurations and roles
STANDARD_CONFIGURATIONS = read_json(os.path.join(os.path.dirname(__file__), "permissions.json"))
STANDARD_ROLES = STANDARD_CONFIGURATIONS["roles"]
STANDARD_PERMISSIONS = STANDARD_CONFIGURATIONS["permissions"]

# gallery workspace has special read-only status for everyone
GALLERY_WORKSPACE_ID = "ws_gallery"


def get_configurations() -> dict:
    """ Return default configuration with list of permissions and roles. """
    return STANDARD_CONFIGURATIONS


def get_standard_item_permission(request: Request, item_type: str) -> str:
    """ Returns the default permission required to access the given item with the given http method """
    assert request
    assert item_type

    if request.method == "GET" or request.method == "HEAD" or request.method == "OPTIONS":
        item_action = "get"
    elif request.method == "POST":
        item_action = "create"
    elif request.method == "PUT" or request.method == "PATCH":
        item_action = "update"
    elif request.method == "DELETE":
        item_action = "delete"
    else:
        raise AnaliticoException(f"get_default_permission: unknown request.method: {request.method}")

    return f"analitico.{item_type}s.{item_action}"


def get_standard_roles_with_permission(permission: str) -> [str]:
    """ Returns a list of standard roles containing the given permission or []. """
    std_roles = []
    for std_role in STANDARD_ROLES:
        if permission in STANDARD_ROLES[std_role]["permissions"]:
            std_roles.append(std_role)
    return std_roles


def get_permitted_queryset(request: Request, item_class: str, permission=None):
    """
    Returns a queryset that will extract all items of the given class
    in any workspace of which the requesting user is either to owner or
    has been given the specific permission directly or via partecipation
    in a role that contains such permission. If a permission is not specified,
    the method will check the standard permission based on item and request
    method, eg. if you're doing a delete on a notebook, the standard permission
    will be 'analitico.notebooks.delete'. 
    """
    # anonymous users have no rights except to read public gallery items
    if request.user.is_anonymous:
        if request.method == "GET" or request.method == "HEAD" or request.method == "OPTIONS":
            if Workspace == item_class:
                return Workspace.objects.filter(id=GALLERY_WORKSPACE_ID)
            else:
                return item_class.objects.filter(workspace__id=GALLERY_WORKSPACE_ID, attributes__icontains='"published":true')
        raise AnaliticoException(
            "Anonymous users can't access this API, please provide authentication credentials or a token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if request.user.is_superuser:
        return item_class.objects.all()

    # find permission and standard roles containing it
    if not permission:
        permission = get_standard_item_permission(request, (item_class()).type)
    if not re.match(r"analitico.[a-z]*\.[a-z]*", permission):
        raise AnaliticoException(
            f"Permission '{permission}' does not look like a valid permission.", status_code=status.HTTP_400_BAD_REQUEST
        )
    roles = get_standard_roles_with_permission(permission)

    # select all items whose workspace is owned by this user OR
    # items on whose workspace the user has a custom permission OR
    # items on whose workspace the user is in a role with required permission
    if Workspace == item_class:
        # we check for rights directly on the workspace itself
        ff = Q(user=request.user)
        ff = ff | Q(roles__user=request.user, roles__permissions__icontains=permission)
        for role in roles:
            ff = ff | Q(roles__user=request.user, roles__roles__icontains=role)
        # add readonly access to ws_gallery which is available to all user
        if request.method == "GET" or request.method == "HEAD" or request.method == "OPTIONS":
            ff = ff | Q(id="ws_gallery")
    else:
        # the items has a reference to the workspace on which we check for rights
        ff = Q(workspace__user=request.user)
        ff = ff | Q(workspace__roles__user=request.user, workspace__roles__permissions__icontains=permission)
        for role in roles:
            ff = ff | Q(workspace__roles__user=request.user, workspace__roles__roles__icontains=role)
        # add readonly access to ws_gallery which is available to all user
        if request.method == "GET" or request.method == "HEAD" or request.method == "OPTIONS":
            ff = ff | (Q(workspace__id="ws_gallery") & Q(attributes__icontains='"published":true'))

    # remove multiple copies of items, sort newer to older
    queryset = item_class.objects.filter(ff).distinct().order_by("-created_at")
    return queryset


def has_item_permission(user, item: ItemMixin, permission: str) -> bool:
    """ Returns true if user has the given permission on the given item. """
    try:
        has_item_permission_or_exception(user, item, permission)
        return True
    except AnaliticoException:
        return False


def has_item_permission_or_exception(user, item: ItemMixin, permission: str) -> bool:
    """ Check if user has the permission required to access the item or raise an exception """
    # anonymous users never have any permissions on any items
    if user.is_anonymous:
        msg = f"Anonymous users do not have '{permission}' permission on '{item.id}'."
        raise AnaliticoException(msg, status_code=status.HTTP_403_FORBIDDEN)

    # superusers have all permissions on all items
    if user.is_superuser:
        return True

    # all users have read permission on the gallery and its contents
    if permission.endswith(".get"):
        if item.id == GALLERY_WORKSPACE_ID or (item.workspace and item.workspace.id == GALLERY_WORKSPACE_ID):
            return True

    # if the item on which we're checking rights is a user itself
    # then only a user himself can change his own record
    if isinstance(item, User):
        return user.email == item.email

    # workspace owner has all permissions on the workspace and all the items owned by the workspace
    workspace = item if isinstance(item, Workspace) else item.workspace
    assert workspace
    if workspace.user == user:
        return True

    # check if the owner of the workspace assigned roles and permissions to this user
    # pylint: disable=no-member
    role = Role.objects.filter(user=user, workspace=workspace).first()
    if role:
        # if user has been assigned one or more of the standard roles, we can scan the standard
        # roles and check which of them contains the required permission then we can check if the
        # user has such a role assigned to him
        if role.roles:
            for standard_role in STANDARD_ROLES:
                # user has been granted this standard role?
                if standard_role in role.roles:
                    # standard role has been granted the required permission?
                    if permission in STANDARD_ROLES[standard_role]["permissions"]:
                        return True

        # we can check if the user has the required permission assigned to him as a custom permission
        if role.permissions and (permission in role.permissions):
            return True

    msg = f"{user.email} does not have '{permission}' permission on '{item.id}'."
    raise AnaliticoException(msg, status_code=status.HTTP_403_FORBIDDEN)


class HasApiPermission(permissions.BasePermission):
    """ 
    Checks if the requesting user has a specific APIs permission or 
    the standard permission required for the given method and item class.
    """

    permission = None

    def has_permission(self, request, view):
        """ If we don't know which object we're working on at least we should require authentication """
        return not request.user.is_anonymous

    def has_object_permission(self, request, view, obj):
        """ Return true if caller has required permissions on specific item. """
        assert isinstance(obj, ItemMixin)
        permission = self.permission if self.permission else get_standard_item_permission(request, obj.type)
        return has_item_permission(request.user, obj, permission)
