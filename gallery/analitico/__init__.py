import os
import logging

# default logger used by libraries, etc
logger = logging.getLogger("analitico")

from .constants import *
from .exceptions import *

import analitico.factory
import analitico.utilities
import analitico.mixin
import analitico.plugin
import analitico.dataset
import analitico.status
import analitico.logging

import analitico.sdk

# classes used to represent items in the service
from analitico.models import Item, Dataset, Recipe, Notebook


# from analitico.factory import Item, Dataset, Recipe, Notebook, AnaliticoException

# import utility methods to main namespace
from analitico.metadata import set_metric, set_model_metrics

# DEPRECATED
def authorize(token=None, endpoint=ANALITICO_API_ENDPOINT) -> analitico.factory.Factory:
    """ 
    Returns an API factory which can create datasets, models, run notebooks, plugins, etc.
    You can pass an API token as a parameter or you can set the ANALITICO_API_ENDPOINT environment
    variable with a token that should be used to authorize API calls. By default calls will be
    made to the production environment but you can specify staging or any other endpoint.
    """
    if not token:
        token = os.environ.get("ANALITICO_API_TOKEN", None)
        if not token:
            logger.warning(
                "authorize - you should pass an API token or set the environment variable ANALITICO_API_ENDPOINT"
            )
    return analitico.factory.Factory(token=token, endpoint=endpoint)


#
def authorize_sdk(token=None, endpoint=ANALITICO_API_ENDPOINT, workspace_id: str = None) -> analitico.factory.Factory:
    """ 
    Returns an API factory which can create datasets, models, run notebooks, plugins, etc.
    You can pass an API token as a parameter or you can set the ANALITICO_API_ENDPOINT environment
    variable with a token that should be used to authorize API calls. By default calls will be
    made to the production environment but you can specify staging or any other endpoint.
    """
    if not token:
        token = os.environ.get("ANALITICO_API_TOKEN", None)
        if not token:
            logger.warning(
                "authorize - you should pass an API token or set the environment variable ANALITICO_API_ENDPOINT"
            )
    return analitico.sdk.AnaliticoSDK(token=token, endpoint=endpoint, workspace_id=workspace_id)
