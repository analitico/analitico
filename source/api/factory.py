

from rest_framework.exceptions import NotFound

import api.models

class ModelsFactory():
    """ Factory used to create models with various methods """

    @staticmethod
    def from_type(model_type:str = None):
        """ Creates a new model from its type, eg: workspace, dataset, etc """
        if model_type == 'workspace':
            return api.models.Workspace()
        if model_type == 'dataset':
            return api.models.Dataset()
        if model_type == 'recipe':
            return api.models.Recipe()
        if model_type == 'model':
            return api.models.Model()
        if model_type == 'service':
            return api.models.Service()
        raise NotFound('ItemsFactory.from_type could not find type: ' + model_type)


    @staticmethod
    def from_id(model_id:str):
        """ Loads a model from database given its id whose prefix determines the model type, eg: ws_xxx for Workspace. """
        if id.startswith(api.models.WORKSPACE_PREFIX):
            return api.models.Workspace.objects.get(pk=model_id)
        if id.startswith(api.models.DATASET_PREFIX):
            return api.models.Dataset.objects.get(pk=model_id)
        if id.startswith(api.models.RECIPE_PREFIX):
            return api.models.Recipe.objects.get(pk=model_id)
        if id.startswith(api.models.MODEL_PREFIX):
            return api.models.Model.objects.get(pk=model_id)
        if id.startswith(api.models.SERVICE_PREFIX):
            return api.models.Service.objects.get(pk=model_id)
        raise NotFound('ItemsFactory.from_id could not find id: ' + model_id)


    @staticmethod
    def from_data(model_data:str):
        """ Use a serializer to create a model from its serialized data """
        # TODO
        return model_data
