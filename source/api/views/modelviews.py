import rest_framework

from rest_framework_json_api import filters
from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated

import api.models
import api.utilities

from api.models import Model
from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .itemviewsetmixin import ItemViewSetMixin, filterset, ITEM_SEARCH_FIELDS, ITEM_FILTERSET_FIELDS
from .jobviews import JobViewSetMixin
from .notebookviews import NotebookViewSetMixin
from .k8viewsetmixin import K8ViewSetMixin

##
## ModelSerializer
##


class ModelSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Model model (oh man, one is model as in machine learning model, the other a Django model...) """

    class Meta:
        model = Model
        exclude = ("attributes",)

    notebook = serializers.JSONField(required=False, allow_null=True)


##
## ModelViewSet - an immutable object describing a trained recipe, ready for inference
##


class ModelViewSet(
    ItemViewSetMixin, AssetViewSetMixin, JobViewSetMixin, NotebookViewSetMixin, K8ViewSetMixin, rest_framework.viewsets.ModelViewSet
):
    """ A trained machine learning model with its training information, recipe and file assets """

    item_class = api.models.Model
    serializer_class = ModelSerializer

    ordering = ("-updated_at",)
    search_fields = ITEM_SEARCH_FIELDS  # defaults
    filterset_fields = ITEM_FILTERSET_FIELDS  # defaults

    # The only action that can be performed on a recipe is to train it
    job_actions = ("train",)
