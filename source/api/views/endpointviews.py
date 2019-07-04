import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

import api.models
import api.utilities

from analitico import ACTION_PREDICT, ACTION_DEPLOY

from api.models import Endpoint
from api.factory import ServerFactory

from .attributeserializermixin import AttributeSerializerMixin
from .itemviewsetmixin import ItemViewSetMixin, filterset, ITEM_SEARCH_FIELDS, ITEM_FILTERSET_FIELDS
from .jobviews import JobViewSetMixin

##
## EndpointSerializer
##


class EndpointSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Endpoint model """

    class Meta:
        model = Endpoint
        exclude = ("attributes",)


##
## EndpointViewSet - list, detail, post, update and run inferences on endpoints
##


class EndpointViewSet(ItemViewSetMixin, JobViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ An endpoint can be listed, added, removed or used to run inferences on a trained machine learning model. """

    item_class = api.models.Endpoint
    serializer_class = EndpointSerializer
    job_actions = (ACTION_DEPLOY, ACTION_PREDICT)

    ordering = ("-updated_at",)
    search_fields = ITEM_SEARCH_FIELDS  # defaults
    filterset_fields = ITEM_FILTERSET_FIELDS  # defaults

    @action(methods=["post"], detail=True, url_name="predict", url_path="predict")
    def predict(self, request, pk):
        """ Runs a synchronous prediction on an endpoint TEMPORARY, WILL DEPRECATE AS SOON AS WE DO KNATIVE """
        with ServerFactory(request=request) as factory:
            endpoint = self.get_object()
            results = endpoint.run(None, factory)
        return Response(results)
