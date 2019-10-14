import analitico
from analitico import AnaliticoException

from .item import Item
from .workspace import Workspace
from .dataset import Dataset
from .recipe import Recipe
from .notebook import Notebook


def models_factory(sdk, item_data: dict) -> Item:
    """
    Create an analitico model from the json response returned by the service.
    
    Arguments:
        item_data {dict} -- Json returned by service. Should contain id, type, attributes.
    
    Returns:
        Item -- An item, eg: Dataset, Recipe, Notebook or generic Item.
    """
    if not "type" in item_data:
        raise AnaliticoException(
            "An item should have a type field, eg: analitico/dataset, analitico/recipe, analitico/notebook, etc."
        )

    if item_data["type"] == "analitico/" + analitico.WORKSPACE_TYPE:
        return Workspace(sdk, item_data)
    if item_data["type"] == "analitico/" + analitico.DATASET_TYPE:
        return Dataset(sdk, item_data)
    if item_data["type"] == "analitico/" + analitico.RECIPE_TYPE:
        return Recipe(sdk, item_data)
    if item_data["type"] == "analitico/" + analitico.NOTEBOOK_TYPE:
        return Notebook(sdk, item_data)

    # generic untyped item
    return Item(sdk, item_data)
