import collections
import jsonfield

from django.db import models
from django.utils.crypto import get_random_string

import analitico
from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace

##
## Model - a trained machine learning model (not model in the sense of Django db model)
##


def generate_model_id():
    return analitico.MODEL_PREFIX + get_random_string()


class Model(ItemMixin, ItemAssetsMixin, models.Model):
    """
    A trained machine learning model which can be used for inferences.
    The "training" attribute of the model includes all the information on
    the training data, parameters, scores and performances. The model can also
    has /data assets like saved CatBoost models, CoreML dumps, etc.
    Trained models are used as immutables in that once created their data
    doesn't change. When you run a new training session you create a new
    model. An endpoint will point to a model to use for predictions. When
    a new model is created, the endpoint is updated to point to the new model.
    """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_model_id)

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Description (markdown supported)
    description = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by ItemMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    # A model's notebook describes the recipe used for training and predictions
    notebook = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)
