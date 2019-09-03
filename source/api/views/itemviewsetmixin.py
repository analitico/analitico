import io
import tempfile

from PIL import Image
from pathlib import Path
from django.http.response import HttpResponse
from django.shortcuts import redirect

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.request import Request

import api

from analitico import AnaliticoException, logger
from api.notifications import slack_oauth_exchange_code_for_token
from api.permissions import HasApiPermission, get_permitted_queryset, has_item_permission_or_exception
from api.utilities import get_query_parameter, get_query_parameter_as_int, image_open, image_resize
from api.libcloud.utilities import clone_files
from api.factory import factory


class filterset:
    """ Premade lists of filters to be used in filterset_fields """

    # https://django-filter.readthedocs.io/en/latest/ref/filterset.html#declaring-filterable-fields
    ALL = ("lt", "gt", "gte", "lte", "in", "icontains", "contains", "iexact", "exact")
    DATE = ("lt", "gt", "gte", "lte", "in", "icontains", "contains", "iexact", "exact")
    TEXT = ("lt", "gt", "gte", "lte", "in", "icontains", "contains", "iexact", "exact")
    ATTRIBUTES = ("icontains", "contains", "iexact", "exact")


# Default search fields
ITEM_SEARCH_FIELDS = ("id", "title", "attributes")

# Default query filters
ITEM_FILTERSET_FIELDS = {
    "id": filterset.ALL,
    "title": filterset.ALL,
    "workspace__id": ["exact"],
    "attributes": filterset.ATTRIBUTES,
    "created_at": filterset.DATE,
    "updated_at": filterset.DATE,
}


##
## ItemViewSetMixin
##


class ItemViewSetMixin:
    """ Basic features for a viewset using as base model api.models.ItemMixin """

    # Defined in subclass, eg: api.models.Endpoint
    item_class = None

    # Defined in subclass, eg: EndpointSerializer
    serializer_class = None

    # All methods require prior authentication, no token, no access
    permission_classes = (IsAuthenticated, HasApiPermission)

    # Default format for requests is json
    format_kwarg = "json"

    def get_queryset(self):
        """
        Returns a list of items that are owned by a workspace which in turn is owned by
        the requesting user. We also add items which are not owned by the user but for
        which the user has been granted the required permission or belongs to a role that
        contains the required permission.
        """
        return get_permitted_queryset(self.request, self.item_class)

    ##
    ## Avatar action
    ##

    # TODO cache avatar images on disk #378
    @action(methods=["get"], detail=True, url_name="avatar", url_path="avatar", permission_classes=(AllowAny,))
    def avatar(self, request, pk):
        """ Returns an item's avatar (if configured) """
        item = self.get_object()

        # users can add an avatar.jpg or avatar.png image to the recipe, dataset or notebook files
        # access to item's avatar requires proper permissions for the item
        # the route is open so that users can retrieve avatars for the public
        # gallery anonymously
        image = None
        for image_name in ("/avatar.png", "/avatar.jpg"):
            if not image:
                try:
                    with tempfile.NamedTemporaryFile(suffix=Path(image_name).suffix) as f:
                        item.download(image_name, f.name)
                        image = Image.open(f.name)
                except Exception as exc:
                    logger.warning(f"avatar - {item.id} doesn't have {image_name}, exc: {exc}")

        # if we don't find the custom image, use default avatars
        if not image:
            default_url = f"https://analitico.ai/assets/avatar-{item.type}.png"
            image = image_open(default_url)

        # additional query parameters can specify how to resize/crop
        # avatars are resized by specifying the height, not the width
        square = get_query_parameter_as_int(request, "square", default=None)
        width = get_query_parameter_as_int(request, "width", default=None)
        height = get_query_parameter_as_int(request, "height", default=None)
        image = image_resize(image, square, width, height)

        imagefile = io.BytesIO()
        image.save(imagefile, format="PNG")
        imagedata = imagefile.getvalue()
        return HttpResponse(imagedata, content_type="image/png")

    ##
    ## Slack integration (oauth redirect url)
    ##

    @action(methods=["get"], detail=True, url_name="slack-oauth", url_path="slack/oauth", permission_classes=[AllowAny])
    def slack_oauth(self, request, pk):
        """ Handles oauth redirects to establish Slack integration with item. """
        has_token = slack_oauth_exchange_code_for_token(request, pk)
        logger.info(f"{request.build_absolute_uri()}, has_token? {has_token}")
        return redirect(f"/app/workspaces/{pk}/settings")

    ##
    ## Cloning items
    ##

    @action(methods=["get"], detail=True, url_name="clone", url_path="clone")
    def clone(self, request: Request, pk: str) -> Response:
        """
        Clones this item and all its file assets. The cloned item will be returned and will have
        a new id. By default the item is cloned in the same workspace, optionally you can specify
        ?workspace_id= to have it cloned to that specific workspace (on which you'll need permissions).
        
        Returns:
            Response -- The cloned item.
        """
        item = self.get_object()
        if isinstance(item, api.models.Workspace):
            raise AnaliticoException("You cannot clone a workspace", status_code=status.HTTP_400_BAD_REQUEST)

        # normally the item is clone is its own workspace. if the ?workspace_id= parameter is
        # specified then we can clone the item in a different workspace but we need to make sure
        # we have create permissions for the particular type of item in the target workspace
        workspace_id = api.utilities.get_query_parameter(request, "workspace_id", item.workspace.id)
        workspace = api.factory.factory.get_item(workspace_id)
        create_permission = f"analitico.{item.type}s.create"
        has_item_permission_or_exception(request.user, workspace, create_permission)

        # clone item in target workspace
        clone = api.factory.factory.get_item(item.id)  # get a copy
        clone.workspace = workspace
        clone.id = None
        clone.save()

        # clone file assets
        clone_files(item, clone)

        # pylint: disable=not-callable
        serializer = self.serializer_class(clone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
