"""
Views and ViewSets for API models
"""

import rest_framework
from rest_framework import serializers

import api.models
import api.utilities

from api.models import Dataset, Job
from .mixins import AssetsViewSetMixin, AttributesSerializerMixin, JobsViewSetMixin


##
## DatasetSerializer
##


class DatasetSerializer(AttributesSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Dataset model """

    class Meta:
        model = Dataset
        exclude = ("attributes",)


##
## DatasetViewSet - list, detail, post and update datasets
##


class DatasetViewSet(AssetsViewSetMixin, JobsViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """
    A dataset model is used to store information on a dataset which is a plugin
    or collection of plugins that can extract, transform and load (ETL) a data source
    and produce clean data which is then used for example to train a model. A dataset
    exposes the same endpoints as all other models + specific endpoints to load
    and deal with file assets.
    """

    item_class = api.models.Dataset
    serializer_class = DatasetSerializer
    job_actions = ("process",)

    def get_queryset(self):
        """ A user only has access to objects he or his workspaces own. """
        if self.request.user.is_anonymous:
            return Dataset.objects.none()
        if self.request.user.is_superuser:
            return Dataset.objects.all()
        return Dataset.objects.filter(workspace__user=self.request.user)

    def _create_job(self, request, job_item, job_action):
        job = super()._create_job(request, job_item, job_action)
        job.status = Job.JOB_STATUS_PROCESSING
        job.save()
        # TODO process job synchronously
        return job
