""" JobSerializer and JobViewSet classes """

import rest_framework
from rest_framework import serializers

import api.models
import api.utilities

from api.models import Dataset, Job
from api.factory import ModelsFactory
from .mixins import AssetsViewSetMixin, AttributesSerializerMixin


##
## JobSerializer
##


class JobSerializer(AttributesSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Job model """

    class Meta:
        model = Job
        exclude = ("attributes",)

    def to_representation(self, item):
        """ Add link to job target as a "related" link. """
        data = super().to_representation(item)
        if "links" in data and item.item_id:
            target = ModelsFactory.from_id(item.item_id)
            data["links"]["related"] = self.get_item_url(target)
        return data


##
## JobViewSet - list, detail, post and update jobs
##


class JobViewSet(AssetsViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ A job can be created, listed, updated, cancelled, etc. """

    item_class = api.models.Job
    serializer_class = JobSerializer

    def get_queryset(self):
        """ A user only has access to jobs he or his workspaces owns. """
        if self.request.user.is_anonymous:
            return Job.objects.none()
        if self.request.user.is_superuser:
            return Job.objects.all()
        return Job.objects.filter(workspace__user=self.request.user)
