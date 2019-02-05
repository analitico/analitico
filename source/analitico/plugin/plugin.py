import logging
import pandas
import tempfile
import os.path
import shutil
import urllib.request
import re
import requests
import json
import tempfile

import urllib.parse
from urllib.parse import urlparse
from abc import ABC, abstractmethod

# Design patterns:
# https://github.com/faif/python-patterns

from analitico.mixin import AttributeMixin

##
## IPluginManager
##


class IPluginManager(ABC, AttributeMixin):
    """ A base abstract class for a plugin lifecycle manager and runtime environment """

    # Authorization token to be used when calling analitico APIs
    token = None

    # APIs endpoint, eg: https://analitico.ai/api/
    endpoint = None

    # Temporary directory used during plugin execution
    _temporary_directory = None

    def __init__(self, token=None, endpoint=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if token:
            assert token.startswith("tok_")
            self.token = token
        if endpoint:
            assert endpoint.startswith("http")
            self.endpoint = endpoint

    ##
    ## Plugins
    ##

    @abstractmethod
    def create_plugin(self, name: str, **kwargs):
        """ A factory method that creates a plugin from its name and settings (builder pattern) """
        pass

    def get_temporary_directory(self):
        """ Temporary directory that can be used while a plugin runs and is deleted afterwards """
        if self._temporary_directory is None:
            self._temporary_directory = tempfile.mkdtemp()
        return self._temporary_directory

    def get_artifacts_directory(self):
        """ 
        An plugin can produce various file artifacts during execution and place
        them in this directory (datasets, statistics, models, etc). If the execution 
        is completed succesfully, a subclass of IPluginManager may persist this 
        information to storage, etc. A file, eg: data.csv, can have a "sister" file
        data.csv.info that contains json metadata (eg: a model may have a sister
        file containing the model's training time, stats, etc).
        """
        artifacts = os.path.join(self.get_temporary_directory(), "artifacts")
        if not os.path.isdir(artifacts):
            os.mkdir(artifacts)
        return artifacts

    def get_cache_directory(self):
        """ Returns directory to be used for caches """
        # method is separate from temp in case we later decide to share local caches
        return self.get_temporary_directory()

    ##
    ## URL retrieval, authorization and caching
    ##

    # regular expression used to detect assets using analitico:// scheme
    ANALITICO_ASSET_RE = r"(analitico://workspaces/(?P<workspace_id>[-\w.]{4,256})/)"

    def get_url(self, url) -> str:
        """
        If the url uses the analitico:// scheme for assets stored on the cloud
        service, it will convert the url to a regular https:// scheme.
        If the url points to an analitico API call, the request will have the
        ?token= authorization token header added to it.
        """
        # temporarily while all internal urls are updated to analitico://
        if url.startswith("workspaces/ws_"):
            url = ANALITICO_PREFIX + url

        # see if assets uses analitico://workspaces/... scheme
        if url.startswith("analitico://"):
            if not self.endpoint:
                raise PluginError(
                    "Plugin manager was not been configured with an API endpoint therefore it cannot process: " + url
                )
            url = self.endpoint + url[len("analitico://") :]
        return url

    def get_url_stream(self, url):
        """
        Returns a stream to the given url. This works for regular http:// or https://
        and also works for analitico:// assets which are converted to calls to the given
        endpoint with proper authorization tokens. The stream is returned as an iterator.
        """
        url = self.get_url(url)
        try:
            url_parse = urlparse(url)
        except Exception as exc:
            pass
        if url_parse and url_parse.scheme in ("http", "https"):
            headers = {}
            if url_parse.hostname and url_parse.hostname.endswith("analitico.ai") and self.token:
                # if url is connecting to analitico.ai add token
                headers = {"Authorization": "Bearer " + self.token}
            response = requests.get(url, stream=True, headers=headers)
            return response.raw
        return open(url, "rb")

    def get_url_json(self, url):
        url_stream = self.get_url_stream(url)
        with tempfile.NamedTemporaryFile() as tf:
            for b in url_stream:
                tf.write(b)
            tf.seek(0)
            return json.load(tf)

    ##
    ## Factory methods
    ##

    @abstractmethod
    def get_dataset(self, dataset_id):
        return None

    ##
    ## with IPluginManager as lifecycle methods
    ##

    def __enter__(self):
        # setup
        return self

    def __exit__(self, type, value, traceback):
        """ Delete any temporary files upon exiting """
        if self._temporary_directory:
            shutil.rmtree(self._temporary_directory, ignore_errors=True)


##
## IPlugin - base class for all plugins
##


class IPlugin(ABC, AttributeMixin):
    """ Abstract base class for Analitico plugins """

    class Meta:
        """ Plugin metadata is exposed in its inner class """

        name = None

    # Manager that provides environment and lifecycle services
    manager: IPluginManager = None

    @property
    def name(self):
        assert self.Meta.name
        return self.Meta.name

    @property
    def logger(self):
        """ Logger that can be used by the plugin to communicate errors, etc with host """
        return logging.getLogger(self.name)

    def __init__(self, manager: IPluginManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager

    def activate(self, *args, **kwargs):
        """ Called when the plugin is initially activated """
        pass

    @abstractmethod
    def run(self, *args, **kwargs):
        """ Run will do in the subclass whatever the plugin does """
        pass

    def deactivate(self, *args, **kwargs):
        """ Called before the plugin is deactivated and finalized """
        pass

    def __str__(self):
        return self.name


##
## IDataframeSourcePlugin - base class for plugins that create dataframes
##


class IDataframeSourcePlugin(IPlugin):
    """ A plugin that creates a pandas dataframe from a source (eg: csv file, sql query, etc) """

    class Meta(IPlugin.Meta):
        inputs = None
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    @abstractmethod
    def run(self, *args, **kwargs):
        """ Run creates a dataset from the source and returns it """
        pass


##
## IDataframePlugin - base class for plugins that manipulate pandas dataframes
##


class IDataframePlugin(IPlugin):
    """
    A plugin that takes a pandas dataframe as input,
    manipulates it and returns a pandas dataframe
    """

    class Meta(IPlugin.Meta):
        inputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    def run(self, *args, **kwargs) -> pandas.DataFrame:
        assert isinstance(args[0], pandas.DataFrame)
        return args[0]


##
## IRecipePlugin - base class for machine learning recipes that can produce trained models
##


class IRecipePlugin(IPlugin):
    """
    A plugin that takes a pandas dataframe as input including labels
    and train a model or a pandas dataframe and run predictions based on a trained model
    """

    class Meta(IPlugin.Meta):
        inputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    def run(self, *args, **kwargs) -> pandas.DataFrame:
        assert isinstance(args[0], pandas.DataFrame)
        return args[0]


##
## IGroupPlugin
##


class IGroupPlugin(IPlugin):
    """ 
    A composite plugin that joins multiple plugins into a functional block,
    for example a processing pipeline made of plugins or a graph workflow. 
    
    *References:
    https://en.wikipedia.org/wiki/Composite_pattern
    https://infinitescript.com/2014/10/the-23-gang-of-three-design-patterns/
    """

    plugins = []

    def __init__(self, manager: IPluginManager, plugins, *args, **kwargs):
        """ Initialize group and create all this plugin's children """
        super().__init__(manager=manager, *args, **kwargs)
        self.plugins = []
        for plugin in plugins:
            if isinstance(plugin, dict):
                plugin = self.manager.create_plugin(**plugin)
            self.plugins.append(plugin)


##
## PluginError
##


class PluginError(Exception):
    """ Exception generated by a plugin; carries plugin info, inner exception """

    # Plugin error message
    message: str = None

    # Plugin that generated this error (may not be defined)
    plugin: IPlugin = None

    def __init__(self, message, plugin: IPlugin = None, exception: Exception = None):
        super().__init__(message, exception)
        self.message = message
        if plugin:
            self.plugin = plugin
            plugin.logger.error(message)

    def __str__(self):
        if self.plugin:
            return self.plugin.name + ": " + self.message
        return self.message
