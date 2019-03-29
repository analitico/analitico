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


class RecipeViewSet(ItemViewSetMixin, JobViewSetMixin, LogViewSetMixin, NotebookViewSetMixin, rest_framework.viewsets.ModelViewSet):
    """
    A recipe contains a pipeline of plugins that can take some training data
    and use it to train a model. When the training action is performed, the result
    will be a new Model item containing all the various artifacts of the training.
    """

    item_class = api.models.Recipe
    serializer_class = RecipeSerializer

    @permission_classes((IsAuthenticated,))
    @action(methods=["post"], detail=True, url_name="detail-train", url_path="train")
    def train(self, request, pk) -> Response:
        """ Create a model from recipe and the job that will train it """

        # verify credentials on recipe
        recipe = self.get_object()

        # create a model which will host the recipe pipeline,
        # training results and training artifacts as assets
        model = Model(workspace=recipe.workspace)
        model.set_attribute("recipe_id", recipe.id)
        model.set_attribute("plugin", recipe.get_attribute("plugin"))
        model.set_notebook(recipe.get_notebook())
        model.save()

        # create and return job that will train the model
        job = self.create_job(request, model, ACTION_TRAIN)
        job.set_attribute("recipe_id", recipe.id)
        job.set_attribute("model_id", model.id)
        job.save()

        # a job is executed asynchronously, potentially on another server
        # and may update the model in the database while we keep holding
        # a reference to a stale and out of date object, so refresh first
        model = Model.objects.get(pk=model.id)
        model.set_attribute("job_id", job.id)
        model.save()

        jobs_serializer = JobSerializer(job)
        return Response(jobs_serializer.data)
