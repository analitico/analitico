from rest_framework.exceptions import NotFound

import api.models

from analitico.utilities import logger

##
## ModelsFactory
##


class ModelsFactory:
    """ Factory used to create models with various methods """

    # pylint: disable=no-member

    @staticmethod
    def get_item_class_from_id(item_id: str):
        """ Returns item class from item id """
        assert item_id
        if item_id.startswith(api.models.DATASET_PREFIX):
            return api.models.Dataset
        if item_id.startswith(api.models.ENDPOINT_PREFIX):
            return api.models.Endpoint
        if item_id.startswith(api.models.JOB_PREFIX):
            return api.models.Job
        if item_id.startswith(api.models.MODEL_PREFIX):
            return api.models.Model
        if item_id.startswith(api.models.RECIPE_PREFIX):
            return api.models.Recipe
        if item_id.startswith(api.models.WORKSPACE_PREFIX):
            return api.models.Workspace
        logger.warning("ModelsFactory.get_class_from_id could not find class for id: " + item_id)
        return None

    @staticmethod
    def get_item_type_from_id(item_id: str):
        assert item_id
        item_class = ModelsFactory.get_item_class_from_id(item_id)
        return item_class._meta.model_name if item_class else None

    @staticmethod
    def from_id(item_id: str, request=None):
        """ Loads a model from database given its id whose prefix determines the model type, eg: ws_xxx for Workspace. """
        # TODO limit access to objects available with request credentials
        assert item_id
        if item_id.startswith(api.models.DATASET_PREFIX):
            return api.models.Dataset.objects.get(pk=item_id)
        if item_id.startswith(api.models.ENDPOINT_PREFIX):
            return api.models.Endpoint.objects.get(pk=item_id)
        if item_id.startswith(api.models.JOB_PREFIX):
            return api.models.Job.objects.get(pk=item_id)
        if item_id.startswith(api.models.MODEL_PREFIX):
            return api.models.Model.objects.get(pk=item_id)
        if item_id.startswith(api.models.RECIPE_PREFIX):
            return api.models.Recipe.objects.get(pk=item_id)
        if item_id.startswith(api.models.WORKSPACE_PREFIX):
            return api.models.Workspace.objects.get(pk=item_id)
        raise NotFound("ModelsFactory.from_id could not find id: " + item_id)
