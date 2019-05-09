import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import api.models
import api.utilities

from analitico import ACTION_TRAIN
from api.models import Recipe, Job, Model
from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .itemviewsetmixin import ItemViewSetMixin
from .jobviews import JobViewSetMixin, JobSerializer
from .logviews import LogViewSetMixin
from .notebookviews import NotebookViewSetMixin

##
## RecipeSerializer
##


class RecipeSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Recipe model """

    class Meta:
        model = Recipe
        exclude = ("attributes",)

    notebook = serializers.JSONField(required=False, allow_null=True)


##
## RecipeViewSet - list, detail, post, update and run training jobs on datasets
##


class RecipeViewSet(
    ItemViewSetMixin, JobViewSetMixin, LogViewSetMixin, NotebookViewSetMixin, rest_framework.viewsets.ModelViewSet
):
    """
    A recipe contains a pipeline of plugins that can take some training data
    and use it to train a model. When the training action is performed, the result
    will be a new Model item containing all the various artifacts of the training.
    """

    item_class = api.models.Recipe
    serializer_class = RecipeSerializer
    job_actions = (ACTION_TRAIN,)
