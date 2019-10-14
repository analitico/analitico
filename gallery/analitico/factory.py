import tempfile
import os
import os.path
import requests
import json
import re
import logging
import hashlib
import inspect
import urllib.parse
import io
import pandas as pd
import tempfile

from .mixin import AttributeMixin
from .exceptions import AnaliticoException
from .status import STATUS_FAILED

import analitico.utilities
from analitico.dataset import Dataset
from analitico.utilities import id_generator

# read http streams in chunks
HTTP_BUFFER_SIZE = 32 * 1024 * 1024  # 32 MiBs


class Factory(AttributeMixin):
    """ A base class providing runtime services like notebook and plugin creation, storage, network, etc """

    def __init__(self, token=None, endpoint=None, **kwargs):
        super().__init__(**kwargs)
        if token:
            assert token.startswith("tok_")
            self.set_attribute("token", token)
        if endpoint:
            assert endpoint.startswith("http")
            self.set_attribute("endpoint", endpoint)

        # use current working directory at the time when the factory
        # is created so that the caller can setup a temp directory we
        # should work in
        self._artifacts_directory = os.getcwd()

    ##
    ## Properties and factory context
    ##

    @property
    def logger(self):
        """ Returns logger wrapped into an adapter that adds contextual information from the factory """
        return self.get_logger()

    @property
    def job(self):
        """ Job running on the server (optional) """
        return self.get_attribute("job")

    @property
    def workspace(self):
        """ Workspace context in which this factory runs (optional) """
        return self.get_attribute("workspace")

    @property
    def token(self):
        """ API token used to call endpoint (optional) """
        return self.get_attribute("token")

    @property
    def endpoint(self):
        """ Endpoint used to call analitico APIs """
        return self.get_attribute("endpoint")

    @property
    def request(self):
        """ Request used as context when running on the server or running async jobs (optional) """
        return self.get_attribute("request")

    ##
    ## Temp and cache directories
    ##

    # Temporary directory which is deleted when factory is disposed
    _temp_directory = None

    # Artifacts end up in the current working directory
    _artifacts_directory = None

    def get_temporary_directory(self):
        """ Temporary directory that can be used while a factory is used and deleted afterwards """
        temp_dir = os.path.join(tempfile.gettempdir(), "analitico_temp")
        if not os.path.isdir(temp_dir):
            os.mkdir(temp_dir)
        return temp_dir

    def get_artifacts_directory(self):
        """ 
        A plugin or notebook can produce various file artifacts during execution and place
        them in this directory (datasets, statistics, models, etc). A subclass, for example
        a factory used to run pipelines on the server, may persist files created here to cloud, etc.
        """
        return self._artifacts_directory

    def get_cache_directory(self):
        """ Returns directory to be used for caches """
        cache_dir = os.path.join(tempfile.gettempdir(), "analitico_cache")
        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)
        return cache_dir

    def get_cache_filename(self, unique_id):
        """ Returns the fullpath in cache for an item with the given unique_id (eg: a unique url, an md5 or etag, etc) """
        # Tip: if cache contents need to be invalidated for whatever reason, you can change the prefix below...
        return os.path.join(self.get_cache_directory(), "cache_v2_" + hashlib.sha256(unique_id.encode()).hexdigest())

    ##
    ## URL retrieval, authorization and caching
    ##

    # regular expression used to detect assets using analitico:// scheme
    ANALITICO_ASSET_RE = r"(analitico://workspaces/(?P<workspace_id>[-\w.]{4,256})/)"

    # TODO could check if it would be possible to switch to an external caching library, eg:
    # https://github.com/ionrock/cachecontrol

    def get_cached_stream(self, stream, unique_id):
        """ Will cache a stream on disk based on a unique_id (like md5 or etag) and return file stream and filename """
        cache_file = self.get_cache_filename(unique_id)
        if not os.path.isfile(cache_file):
            # if not cached already, download and cache
            cache_temp_file = cache_file + ".tmp_" + id_generator()

            with open(cache_temp_file, "wb") as f:
                if hasattr(stream, "read"):
                    for chunk in iter(lambda: stream.read(HTTP_BUFFER_SIZE), b""):
                        f.write(chunk)
                else:
                    for b in stream:
                        f.write(b)

            # TODO add progress bar for slow downloads https://github.com/tqdm/tqdm#iterable-based

            os.rename(cache_temp_file, cache_file)
        # return stream from cached file
        return open(cache_file, "rb"), cache_file

    def get_url_stream(self, url, binary=False, cache=True):
        """
        Returns a stream to the given url. This works for regular http:// or https://
        and also works for analitico:// assets which are converted to calls to the given
        endpoint with proper authorization tokens. The stream is returned as an iterator.
        """
        assert url and isinstance(url, str)
        # If the url uses the analitico:// scheme for assets stored on the cloud
        # service, it will convert the url to a regular https:// scheme.
        # If the url points to an analitico API call, the request will have the
        # ?token= authorization token header added to it.
        # temporarily while all internal urls are updated to analitico://
        if url.startswith("workspaces/ws_"):
            url = analitico.ANALITICO_URL_PREFIX + url
        # see if assets uses analitico://workspaces/... scheme
        if url.startswith("analitico://"):
            if not self.endpoint:
                raise Exception("Factory is not configured with a valid API endpoint and cannot get: " + url)
            url = self.endpoint + url[len("analitico://") :]

        try:
            url_parse = urllib.parse.urlparse(url)
        except Exception:
            pass
        if url_parse and url_parse.scheme in ("http", "https"):
            headers = {}
            if url_parse.hostname and url_parse.hostname.endswith("analitico.ai") and self.token:
                # if url is connecting to analitico.ai add token
                headers = {"Authorization": "Bearer " + self.token}

            # we should not take the raw response stream here as it could be gzipped or encoded.
            # we take the decoded content as a text string and turn it into a stream or we take the
            # decompressed binary content and also turn it into a stream.
            response = requests.get(url, stream=True, headers=headers)

            # always treat content as binary, utf-8 encoding is done by readers
            response_stream = io.BytesIO(response.content)

            if cache and "etag" in response.headers:
                etag = response.headers["etag"]
                if etag:
                    return self.get_cached_stream(response_stream, url + etag)[0]
            return response_stream
        return open(url, "rb")

    def get_url_json(self, url):
        assert url and isinstance(url, str)
        url_stream = self.get_url_stream(url)
        return json.load(url_stream, encoding="utf-8")

    ##
    ## Plugins
    ##

    # dictionary of registered plugins name:class
    __plugins = {}

    @staticmethod
    def register_plugin(plugin):
        if inspect.isabstract(plugin):
            print("Factory.register_plugin: %s is abstract and cannot be registered" % plugin.Meta.name)
            return
        if plugin.Meta.name not in Factory.__plugins:
            Factory.__plugins[plugin.Meta.name] = plugin
            # print("Plugin: %s registered" % plugin.Meta.name)

    def get_plugin(self, name: str, **kwargs):
        """
        Create a plugin given its name and the environment it will run in.
        Any additional parameters passed to this method will be passed to the
        plugin initialization code and will be stored as a plugin setting.
        """
        try:
            # deprecated, temporary retrocompatibility 2019-02-24
            if name == "analitico.plugin.AugmentDatesDataframePlugin":
                name = "analitico.plugin.AugmentDatesPlugin"
            if name not in Factory.__plugins:
                self.exception("Factory.get_plugin - %s is not a registered plugin", name)
            return (Factory.__plugins[name])(factory=self, **kwargs)
        except Exception as exc:
            self.exception("Factory.get_plugin - error while creating " + name, exception=exc)

    def run_plugin(self, *args, settings, **kwargs):
        """ 
        Runs a plugin and returns its results. Takes a number of positional and named arguments
        which are passed to the plugin for execution and a dictionary of settings used to create
        the plugin. If settings are passed as an array, the method will create a pipeline plugin
        which will execute the plugins in a chain.
        """
        if isinstance(settings, list):
            settings = {"name": "analitico.plugin.PipelinePlugin", "plugins": settings}
        plugin = self.get_plugin(**settings)
        return plugin.run(*args, **kwargs)

    def get_plugins(self):
        """ Returns a list of registered plugin classes """
        return Factory.__plugins

    ##
    ## Factory methods
    ##

    EMAIL_RE = r"[^@]+@[^@]+\.[^@]+"  # very rough check

    def get_item_type(self, item_id):
        """ Returns item class from item id, eg: returns 'dataset' from ds_xxx """
        assert item_id and isinstance(item_id, str)
        if item_id.startswith(analitico.DATASET_PREFIX):
            return analitico.DATASET_TYPE
        if item_id.startswith(analitico.ENDPOINT_PREFIX):
            return analitico.ENDPOINT_TYPE
        if item_id.startswith(analitico.JOB_PREFIX):
            return analitico.JOB_TYPE
        if item_id.startswith(analitico.MODEL_PREFIX):
            return analitico.MODEL_TYPE
        if item_id.startswith(analitico.NOTEBOOK_PREFIX):
            return analitico.NOTEBOOK_TYPE
        if item_id.startswith(analitico.PLUGIN_PREFIX):
            return analitico.PLUGIN_TYPE
        if item_id.startswith(analitico.RECIPE_PREFIX):
            return analitico.RECIPE_TYPE
        if item_id.startswith(analitico.WORKER_PREFIX):
            return analitico.WORKER_TYPE
        if item_id.startswith(analitico.WORKSPACE_PREFIX):
            return analitico.WORKSPACE_TYPE
        if re.match(self.EMAIL_RE, item_id):
            return analitico.USER_TYPE
        self.warning("Factory.get_item_type - couldn't find type for: " + item_id)
        return None

    def get_item(self, item_id):
        """ Retrieves item from the server by item_id """
        assert item_id and isinstance(item_id, str) and self.endpoint.endswith("/")
        url = "{}{}s/{}".format(self.endpoint, self.get_item_type(item_id), item_id)
        return self.get_url_json(url)

    def get_dataset(self, dataset_id):
        """ Creates a Dataset object from the cloud dataset with the given id """
        plugin_settings = {
            "type": "analitico/plugin",
            "name": "analitico.plugin.CsvDataframeSourcePlugin",
            "source": {"type": "text/csv", "url": "analitico://datasets/{}/data/csv".format(dataset_id)},
        }
        # Instead of creating a plugin that reads the end product of the dataset
        # pipeline we should consider reading the dataset information from its endpoint,
        # getting the entire plugin chain and recreating it here exactly the same so it
        # can be run in Jupyter with all its plugins, etc.
        plugin = self.get_plugin(**plugin_settings)
        return Dataset(self, plugin=plugin)

    ##
    ## Logging
    ##

    class LogAdapter(logging.LoggerAdapter):
        """ A simple adapter which will call "process" on every log record to enrich it with contextual information from the Factory. """

        factory = None

        def __init__(self, logger, factory):
            super().__init__(logger, {})
            self.factory = factory

        def process(self, msg, kwargs):
            return self.factory.process_log(msg, kwargs)

    def process_log(self, msg, kwargs):
        """ Moves any kwargs other than 'exc_info' and 'extra' to 'extra' dictionary. """
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        extra = kwargs["extra"]
        for key in kwargs.copy().keys():
            if key not in ("exc_info", "extra"):
                extra[key] = kwargs.pop(key)

        for attr_name in ("workspace", "token", "endpoint", "request", "job"):
            attr = self.get_attribute(attr_name, None)
            if attr:
                extra[attr_name] = attr
        return msg, kwargs

    def set_logger_level(self, level):
        """ Sets logger level to given level for all future log calls make through the factory logger """
        self.set_attribute("logger_level", level)

    def get_logger(self, name="analitico"):
        """ Returns logger wrapped into an adapter that adds contextual information from the Factory """
        logger_level = self.get_attribute("logger_level", logging.INFO)
        logger = Factory.LogAdapter(logging.getLogger(name), self)
        logger.setLevel(logger_level)
        return logger

    def debug(self, msg, *args, **kwargs):
        self.logger.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.log(logging.ERROR, msg, *args, **kwargs)

    def status(self, item, status, **kwargs):
        """ Updates on the status of an item. Status is one of: created, running, canceled, completed or failed. """
        level = logging.ERROR if status == STATUS_FAILED else logging.INFO
        self.logger.log(level, "status: %s, name: %s", status, type(item).__name__, item=item, status=status, **kwargs)

    def exception(self, msg, *args, **kwargs):
        message = msg % (args)
        self.error(msg, *args, **kwargs)
        exception = kwargs.get("exception", None)
        if exception:
            raise AnaliticoException(message, **kwargs) from exception
        raise AnaliticoException(message, **kwargs)

    ##
    ## with Factory as: lifecycle methods
    ##

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """ Leave any temporary files upon exiting """
        pass

    ##
    ## SDK utility methods
    ##

    def get_dataframe(self, item_id: str) -> pd.DataFrame:
        """ 
        Returns the processed data from the given dataset in Analitico as a pandas DataFrame object. 
        """
        df = self.run_plugin(settings={"name": "analitico.plugin.DatasetSourcePlugin", "dataset_id": item_id})
        return df

    def upload(self, item_id: str, df: pd.DataFrame, filename: str = "data.parquet"):

        # if not (filename.startswith("data/") or filename.startswith("assets/")):
        #    raise AnaliticoException("Filename should start with assets/ or data/")

        item_type = self.get_item_type(item_id)
        url = f"{self.endpoint}{item_type}s/{item_id}/assets/{filename}"

        if filename.endswith(".parquet"):
            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = os.path.join(tmpdir, filename)
                df.to_parquet(filepath)
                response = requests.post(
                    url, files={"file": filepath}, headers={"Authorization": "Bearer " + self.token}
                )
                if response.status_code != 201:
                    raise AnaliticoException(
                        f"Asset {filename} could not be uploaded to item {item_id}", response=response.json()
                    )
        else:
            raise AnaliticoException(f"Did not recognize file format for {filename}")
        return self.get_item(item_id)
