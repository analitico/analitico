import rest_framework

from rest_framework import serializers
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated

import api.models
import api.utilities

from api.models import Model
from .attributeserializermixin import AttributeSerializerMixin
from .assetviewsetmixin import AssetViewSetMixin
from .jobviews import JobViewSetMixin


##
## ModelSerializer
##


class ModelSerializer(AttributeSerializerMixin, serializers.ModelSerializer):
    """ Serializer for Model model (oh man, one is model as in machine learning model, the other a Django model...) """

    class Meta:
        model = Model
        exclude = ("attributes",)


##
## ModelViewSet - list, detail, post, update and run training jobs on datasets
##


class ModelViewSet(JobViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """ A trained machine learning model with its training information and file assets """

    item_class = api.models.Model
    serializer_class = ModelSerializer

    # The only action that can be performed on a recipe is to train it
    job_actions = ("train",)

    # All methods require prior authentication, no token, no access
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """ A user must be authenticated and only only access to objects he or his workspaces own. """
        assert not self.request.user.is_anonymous
        if self.request.user.is_superuser:
            return Model.objects.all()
        return Model.objects.filter(workspace__user=self.request.user)
