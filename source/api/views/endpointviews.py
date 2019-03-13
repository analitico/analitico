import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import APIException

import analitico
import api.models
import api.utilities

from analitico import ACTION_PREDICT

from api.models import Endpoint, Job
from api.factory import ServerFactory
from .attributeserializermixin import AttributeSerializerMixin
from .itemviewsetmixin import ItemViewSetMixin
from .assetviewsetmixin import AssetViewSetMixin
from .jobviews import JobViewSetMixin
from .logviews import LogViewSetMixin

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


class EndpointViewSet(ItemViewSetMixin, JobViewSetMixin, LogViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ An endpoint can be listed, added, removed or used to run inferences on a trained machine learning model. """

    item_class = api.models.Endpoint
    serializer_class = EndpointSerializer

    # The only action that can be performed on an endpoint is an inference
    job_actions = (ACTION_PREDICT,)

    # deprecated
    @action(methods=["post"], detail=True, url_name=ACTION_PREDICT + "OLD", url_path=ACTION_PREDICT + "OLD")
    def predictOLD(self, request, pk):
        """ Runs a synchronous prediction on an endpoint """
        job_item = self.get_object()  # endpoint
        return self.create_job_response(request, job_item, ACTION_PREDICT, run_async=False, just_payload=True)

    @action(methods=["post"], detail=True, url_name="predict", url_path="predict")
    def predict(self, request, pk):
        """ Runs a synchronous prediction on an endpoint """
        with ServerFactory(request=request) as factory:
            endpoint = self.get_object()
            results = endpoint.run(None, factory)
        return Response(results)
