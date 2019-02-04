import analitico.utilities
import analitico.plugin
import analitico.dataset
import analitico.mixin
import analitico.manager

STAGING_API_ENDPOINT = "https://staging.analitico.ai/api/"
API_ENDPOINT = "https://analitico.ai/api/"


def get_manager(token=None, endpoint=STAGING_API_ENDPOINT) -> analitico.plugin.IPluginManager:
    """ Returns a plugin manager which can create datasets, models, plugins, etc """
    return analitico.manager.PluginManager(token, endpoint)
