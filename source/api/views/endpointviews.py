import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import api.models
import api.utilities

from api.models import Endpoint, Job
from .attributeserializermixin import AttributeSerializerMixin
from .itemviews import ItemViewSetMixin
from .assetviewsetmixin import AssetViewSetMixin
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

    # The only action that can be performed on an endpoint is an inference
    job_actions = ("predict",)

    @action(methods=["post"], detail=True, url_name="predict", url_path="predict")
    def predict(self, request, pk):
        data = request.data
        return Response("ciao pippo!")
