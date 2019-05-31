import rest_framework
import rest_framework.viewsets

from rest_framework_json_api import filters
from rest_framework_json_api import django_filters
from rest_framework.filters import SearchFilter

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import MethodNotAllowed

import api.models
import api.utilities

from api.models import Log
from .attributeserializermixin import AttributeSerializerMixin
from .itemviewsetmixin import ItemViewSetMixin, filterset

# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

##
## LogSerializer
##


class LogSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Log model """

    class Meta:
        model = Log
        exclude = ("attributes",)

    def to_representation(self, item):
        """ Add item_id link reference """
        data = super().to_representation(item)
        if item.item_id:
            try:
                data["links"]["item"] = self.get_item_url(item.item_id)
            except Exception:
                pass
        return data


##
## LogViewSetMixin - mixin for listing log entries belonging to an item
##


class LogViewSetMixin:
    """ Adds capability to list log entries related to an item """

    # a user can only read logs attached to items that he owns
    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="log-list", url_path="logs")
    def log_list(self, request, pk) -> Response:
        """ Returns a listing of log entries associated with this item. """
        # we read the item here rather than just filtering with pk
        # because we need to make sure the user making the call has
        # the rights to access this item. if he can access the item
        # then he can also access log items attached to that item
        item = self.get_object()
        logviewset = LogViewSet(request=request)
        return logviewset.list_by_item_id(request, item.id)


##
## LogViewSet - list, detail, post and update log entries
##


class LogViewSet(ItemViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ A log entry can be created, listed, updated, cancelled, etc. """

    # staff can read all logs, users can read logs that belong to their workspaces
    permission_classes = (IsAuthenticated,)

    item_class = api.models.Log
    serializer_class = LogSerializer
    search_fields = ("item_id", "title", "attributes")
    filterset_fields = {
        "id": filterset.ALL,
        "item_id": filterset.ALL,
        "title": filterset.ALL,
        "attributes": filterset.ATTRIBUTES,
        "created_at": filterset.DATE,
    }

    def get_queryset(self):
        """ A user only has access to log entries he or his workspaces owns. Superusers see all log entries. """
        queryset = super().get_queryset().order_by("-created_at")
        if hasattr(self, "item_id"):
            queryset = queryset.filter(item_id=self.item_id)
        return queryset

    def list_by_item_id(self, request, item_id, **kwargs):
        """ Returns logs belonging to a specific item_id with all filters applied """

        # NOTE: caller needs to make sure user has access to item_id
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(item_id=item_id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LogSerializer(queryset, many=True)
        return Response(serializer.data)
