""" JobSerializer and JobViewSet classes """

import rest_framework
from rest_framework import serializers

import api.models
import api.utilities

from api.models import Dataset, Job

from .assetviewsetmixin import AssetViewSetMixin
from .attributeserializermixin import AttributeSerializerMixin

# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import os

from django.utils.text import slugify
from django.http.response import StreamingHttpResponse
from django.utils.http import parse_http_date_safe, http_date
from django.utils.timezone import now
from django.urls import reverse

import rest_framework
import rest_framework.viewsets

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import NotFound, MethodNotAllowed, APIException
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser
from rest_framework import status

from analitico.status import STATUS_CREATED, STATUS_RUNNING, STATUS_COMPLETED, STATUS_COMPLETED
from analitico.utilities import logger, get_dict_dot

from api.models import ItemMixin, Job
from api.factory import factory
from .logviews import LogViewSetMixin
from .itemviewsetmixin import filterset

##
## JobSerializer
##


class JobSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Job model """

    class Meta:
        model = Job
        exclude = ("attributes",)

    def to_representation(self, item):
        """ Add link to job target as a related link. """
        data = super().to_representation(item)

        # Payload as its own dictionary:
        # - pros: easier to find among attributes
        # - cons: breaks pattern with other items
        # payload = data["attributes"].pop("payload", None)
        # data["payload"] = payload

        if "links" in data and item.item_id:
            item_type = factory.get_item_type(item.item_id)
            item_url = self.get_item_url(item.item_id)
            if item_url:
                data["links"][item_type] = item_url
        return data


##
## JobViewSetMixin - endpoints for creating jobs attached to an item, eg: train a model
##


class JobViewSetMixin:
    """
    This is a mixin used by other viewsets like WorkspaceViewSet and DatasetViewSet.
    It provides the endpoint and methods needed to create jobs that are applied to the item,
    for example create a job that will process a dataset or train a model.
    The mixin also lets you list jobs attached to the item or see the status of a specific job.
    """

    # defined in subclass to list acceptable actions
    job_actions = ()

    def create_job(self, request, job_item, job_action, run_async=False):
        workspace_id = job_item.workspace.id if job_item.workspace else job_item.id
        job_action = job_item.type + "/" + job_action
        job_status = STATUS_CREATED if run_async else STATUS_RUNNING
        job = Job(item_id=job_item.id, action=job_action, workspace_id=workspace_id, status=job_status)
        job.save()
        if not run_async:
            job.run(request)
        return job

    def create_job_response(self, request, job_item, job_action, run_async=False, just_payload=False):
        """ Runs a job and creates a response which can be the job itself or just its payload """
        job = self.create_job(request, job_item, job_action, run_async=run_async)
        if job.status == STATUS_COMPLETED and just_payload:
            payload = job.payload
            payload["job_id"] = job.id
            return Response(payload)
        return Response(job)

    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="job-list", url_path="jobs")
    def job_list(self, request, pk) -> Response:
        """ Returns a listing of all jobs associated with this item. """
        jobs = Job.objects.filter(item_id=pk)
        jobs_serializer = JobSerializer(jobs, many=True)
        return Response(jobs_serializer.data)

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="job-action", url_path=r"jobs/(?P<job_action>[-\w.]{4,256})$")
    def job_create(self, request, pk, job_action) -> Response:
        """ Creates a job for this item and returns it. """
        job_item = self.get_object()
        if job_action in self.job_actions:
            job = self.create_job(request, job_item, job_action)
            jobs_serializer = JobSerializer(job)
            return Response(jobs_serializer.data)
        raise MethodNotAllowed(job_item.type + " cannot create a job of type: " + job_action)


##
## JobViewSet - list, detail, post and update jobs
##


class JobViewSet(AssetViewSetMixin, LogViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ A job can be created, listed, updated, cancelled, etc. """

    item_class = api.models.Job
    serializer_class = JobSerializer

    ordering = ("-updated_at",)
    search_fields = ("id", "title", "description", "attributes", "status", "action", "item_id")
    filterset_fields = {
        "id": filterset.ALL,
        "title": filterset.ALL,
        "description": filterset.ALL,
        "created_at": filterset.DATE,
        "updated_at": filterset.DATE,
        "attributes": filterset.ATTRIBUTES,
        "status": filterset.ALL,
        "action": filterset.ALL,
        "item_id": filterset.ALL,
    }

    def get_queryset(self):
        """ A user only has access to jobs he or his workspaces owns. """
        if self.request.user.is_anonymous:
            return Job.objects.none()
        if self.request.user.is_superuser:
            return Job.objects.all()
        return Job.objects.filter(workspace__user=self.request.user)
