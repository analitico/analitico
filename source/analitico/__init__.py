from .constants import *
from .exceptions import *

import analitico.factory
import analitico.utilities
import analitico.mixin
import analitico.plugin
import analitico.dataset
import analitico.status


def authorize(token=None, endpoint=ANALITICO_STAGING_API_ENDPOINT) -> analitico.factory.Factory:
    """ Returns an API factory which can create datasets, models, run notebooks, plugins, etc """
    try:
        # TODO: we could go up the call stack and find the first factory we can and use that

        # import api.factory

        # if we have api.factory installed, it means that we're running in a server or runner
        # context. we should use a server factory which will access models and data directly
        # rather than via APIs. we should not have the factory create its own temporary directory
        # since we're most likely running within the context of a job or notebook which will be
        # cleaned up automatically anyway

        # return api.factory.ServerFactory(token=token, endpoint=endpoint, mkdtemp=False)
        pass
    except:
        pass

    # if server factory is unknown, we're running in Jupyter, Colab or similar
    # and we can use a regular factory with an auth token which will be used to
    # access our data and models via regular API calls
    return analitico.factory.Factory(token=token, endpoint=endpoint)
