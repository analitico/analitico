import io

from django.http.response import HttpResponse
from django.shortcuts import redirect

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.request import Request

import api

from analitico import logger
from api.slack import slack_oauth_exchange_code_for_token, slack_get_install_button_url
from api.permissions import HasApiPermission, get_permitted_queryset
from api.utilities import get_query_parameter, get_query_parameter_as_int, image_open, image_resize


class filterset:
    """ Premade lists of filters to be used in filterset_fields """

    # https://django-filter.readthedocs.io/en/latest/ref/filterset.html#declaring-filterable-fields
    ALL = ("lt", "gt", "gte", "lte", "in", "icontains", "contains", "iexact", "exact")
    DATE = ("lt", "gt", "gte", "lte", "in", "icontains", "contains", "iexact", "exact")
    TEXT = ("lt", "gt", "gte", "lte", "in", "icontains", "contains", "iexact", "exact")
    ATTRIBUTES = ("icontains", "contains", "iexact", "exact")


# Default search fields
ITEM_SEARCH_FIELDS = ("item_id", "title", "attributes")

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

    @action(methods=["get"], detail=True, url_name="avatar", url_path="avatar")
    def avatar(self, request, pk):
        """ Returns an item's avatar (if configured) """
        item = self.get_object()

        square = get_query_parameter_as_int(request, "square", default=None)
        width = get_query_parameter_as_int(request, "width", default=None)
        height = get_query_parameter_as_int(request, "height", default=None)

        # first check if item has its own avatar
        avatar = item.get_attribute("avatar", None)
        if not avatar:
            # default avatar is used if item has none
            avatar = get_query_parameter(request, "default", default=None)
            if not avatar:
                raise NotFound("Item " + item.id + " does not have an avatar", code="no_avatar")

        try:
            image = image_open(avatar)
        except Exception:
            avatar = "https://app.analitico.ai/avatars/" + avatar
            image = image_open(avatar)

        image = image_resize(image, square, width, height)

        imagefile = io.BytesIO()
        image.save(imagefile, format="JPEG")
        imagedata = imagefile.getvalue()

        return HttpResponse(imagedata, content_type="image/jpeg")

    ##
    ## Slack integration (oauth redirect url)
    ##

    @action(methods=["get"], detail=True, url_name="slack-oauth", url_path="slack/oauth", permission_classes=[AllowAny])
    def slack_oauth(self, request, pk):
        """ Handles oauth redirects to establish Slack integration with item. """
        has_token = slack_oauth_exchange_code_for_token(request, pk)
        logger.info(f"{request.build_absolute_uri()}, has_token? {has_token}")
        return redirect(f"/app/workspaces/{pk}/settings")
