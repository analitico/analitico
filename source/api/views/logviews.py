import rest_framework
import rest_framework.viewsets

from rest_framework_json_api import filters
from rest_framework_json_api import django_filters
from rest_framework.filters import SearchFilter

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
## LogViewSetMixin - endpoints for listing log entries
##


class LogViewSetMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to list log entries related to an item 
    or to save log entries and associated them with the specific item.
    """

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="log-list", url_path="logs")
    def log_list(self, request, pk) -> Response:
        """ Returns a listing of log entries associated with this item. """
        logs = Log.objects.filter(item_id=pk)
        logs_serializer = LogSerializer(logs, many=True)
        return Response(logs_serializer.data)

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="job-action", url_path=r"logs/(?P<job_action>[-\w.]{4,256})$")
    def job_create(self, request, pk, job_action) -> Response:
        """ Creates a job for this item and returns it. """
        job_item = self.get_object()
        if job_action in self.job_actions:
            job = self.create_job(request, job_item, job_action)
            jobs_serializer = LogSerializer(job)
            return Response(jobs_serializer.data)
        raise MethodNotAllowed(job_item.type + " cannot create a job of type: " + job_action)


##
## LogViewSet - list, detail, post and update log entries
##


class LogViewSet(ItemViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ A log entry can be created, listed, updated, cancelled, etc. """

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
        if self.request.user.is_anonymous:
            return Log.objects.none()
        if self.request.user.is_superuser:
            return Log.objects.all()
        return Log.objects.filter(workspace__user=self.request.user)
