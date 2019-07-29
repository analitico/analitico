""" JobSerializer and JobViewSet classes """

import requests

import rest_framework
from rest_framework import serializers

import analitico
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
import django.conf

import rest_framework
import rest_framework.viewsets

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import NotFound, MethodNotAllowed, APIException
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser
from rest_framework import status

from analitico.status import STATUS_CREATED, STATUS_RUNNING, STATUS_COMPLETED, STATUS_COMPLETED
from analitico.utilities import logger, get_dict_dot

from api.utilities import get_query_parameter, get_query_parameter_as_bool
from api.models import ItemMixin
from api.models.job import Job, timeout_jobs
from api.factory import factory
from api.k8 import k8_jobs_create, k8_jobs_get, k8_jobs_list, k8_deploy_v2

from .itemviewsetmixin import filterset, ItemViewSetMixin

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

    # DEPRECATED
    @permission_classes((IsAuthenticated,))
    @action(methods=["get"], detail=True, url_name="job-list", url_path="jobs")
    def job_list(self, request, pk) -> Response:
        """ Returns a listing of all jobs associated with this item. """
        # we read the item here instead of just using pk because
        # we need to make sure the user has access rights to it
        item = self.get_object()
        jobs = Job.objects.filter(item_id=item.id)
        jobs_serializer = JobSerializer(jobs, many=True)
        return Response(jobs_serializer.data)

    # DEPRECATED
    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="job-action", url_path=r"jobs/(?P<job_action>[-\w.]{4,256})$")
    def job_create(self, request, pk, job_action) -> Response:
        """ Creates a job for this item and returns it. """
        job_item = self.get_object()
        if job_action not in self.job_actions:
            raise MethodNotAllowed(job_item.type + " cannot create a job of type: " + job_action)

        # caller may have posted some attributes for the job. if so we want
        # to add these to the job. django may have filtered the input and added
        # a "data" wrapper to make the call more json:api compliant, so we need to strip it
        data = request.data
        if data and "data" in data:
            data = data["data"]

        job = job_item.create_job(job_action, data)

        run_async = get_query_parameter_as_bool(request, "async", True)
        if not run_async:
            job.status = STATUS_RUNNING
            job.save()
            analitico.logger.warning(f"Running jobs synchronously is not recommended, item: {job_item.id}")
            job.run(request)

        serializer = JobSerializer(job)
        return Response(serializer.data)

    ##
    ## Kubernetes jobs and service deployment APIs
    ##

    @action(methods=["get", "post"], detail=True, url_name="k8-jobs", url_path=r"k8s/jobs/(?P<job_pk>[-\w.]{0,64})$")
    def k8jobs(self, request: Request, pk: str, job_pk: str) -> Response:
        """
        Create a job, retrieve a specific job, retrieve all jobs for item.
        
        Arguments:
            request {Request} -- The request being posted.
            pk {str} -- The item that we're reading or creating jobs for.
            job_pk {str} -- The job id when getting a specific job, or the job action when creating a job.
        
        Returns:
            Response -- The k8s job that was create or retrieve or a list of jobs for this item.
        """
        item = self.get_object()

        # create a new job
        if self.request.method == "POST":
            job_action = job_pk
            job_data = request.data
            if job_data and "data" in job_data:
                job_data = job_data["data"]
            job = k8_jobs_create(item, job_action, job_data)
            return Response(job, content_type="json")

        job_id = job_pk
        if job_id:
            # retrieve specific job by id
            job = k8_jobs_get(item, job_id, request)
            return Response(job, content_type="json")

        # retrieve list of jobs
        jobs = k8_jobs_list(item, request)
        return Response(jobs, content_type="json")

    @action(methods=["post"], detail=True, url_name="k8-deploy", url_path=r"k8s/deploy/(?P<stage>staging|production)$")
    def k8deploy(self, request: Request, pk: str, stage: str) -> Response:
        """
        Deploy an item that has previously been built into a docker using /k8s/jobs/build, etc...
        
        Arguments:
            request {Request} -- The request being posted.
            pk {str} -- The item that we're reading or creating jobs for.
            stage {str} -- K8_STAGE_PRODUCTION or K8_STAGE_STAGING
        
        Returns:
            Response -- The k8s service that was deployed (or is being deployed asynch).
        """
        item = self.get_object()

        # TODO check for specific deployment permissions

        service = k8_deploy_v2(item, stage)
        return Response(service, content_type="json")


##
## JobViewSet - list, detail, post and update jobs
##


class JobViewSet(ItemViewSetMixin, AssetViewSetMixin, rest_framework.viewsets.ModelViewSet):
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

    @action(methods=["get"], detail=False, url_name="schedule", url_path="schedule", permission_classes=(IsAdminUser,))
    def schedule(self, request):
        """ 
        Check for datasets, recipes or notebook that have cron schedules and creates 
        any jobs to reprocess them if necessary. Cancel any stuck jobs 
        """
        jobs = api.models.job.schedule_jobs()
        jobs_serializer = JobSerializer(jobs, many=True)
        return Response(jobs_serializer.data)
