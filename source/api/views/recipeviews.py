import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated

import api.models
import api.utilities

from api.models import Recipe, Job
from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .jobviews import JobViewSetMixin


##
## RecipeSerializer
##


class RecipeSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Recipe model """

    class Meta:
        model = Recipe
        exclude = ("attributes",)


##
## RecipeViewSet - list, detail, post, update and run training jobs on datasets
##


class RecipeViewSet(JobViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """
    A recipe contains a pipeline of plugins that can take some training data
    and use it to train a model. When the training action is performed, the result
    will be a new Model item containing all the various artifacts of the training.
    """

    item_class = api.models.Recipe
    serializer_class = RecipeSerializer
    job_actions = ("train",)

    def get_queryset(self):
        """ A user only has access to objects he or his workspaces own. """
        if self.request.user.is_anonymous:
            return Recipe.objects.none()
        if self.request.user.is_superuser:
            return Recipe.objects.all()
        return Recipe.objects.filter(workspace__user=self.request.user)
