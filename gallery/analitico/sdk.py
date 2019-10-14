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
import analitico.models

from analitico.utilities import id_generator, logger
from analitico.models import Workspace, Item, Dataset, Recipe, Notebook

##
## Models used in the SDK
##


class AnaliticoSDK(AttributeMixin):
    """ An SDK for analitico.ai/api. """

    def __init__(self, token=None, endpoint=None, workspace_id: str = None, **kwargs):
        super().__init__(**kwargs)
        if token:
            assert token.startswith("tok_")
            self.set_attribute("token", token)
        if endpoint:
            assert endpoint.startswith("https://") or endpoint.startswith("http://")
            assert endpoint.endswith("/")
            self.set_attribute("endpoint", endpoint)

        # set default workspace
        if workspace_id:
            self.workspace = self.get_workspace(workspace_id)

        # use current working directory at the time when the factory
        # is created so that the caller can setup a temp directory we
        # should work in
        self._artifacts_directory = os.getcwd()

    ##
    ## Properties and factory context
    ##

    # default workspace
    _workspace: Workspace = None

    @property
    def workspaces(self) -> [Workspace]:
        """ Returns your workspaces. """
        return self.get_items(analitico.WORKSPACE_TYPE)

    @property
    def workspace(self):
        """ Get the default workspace used by the SDK (for example when creating items). """
        return self._workspace

    @workspace.setter
    def workspace(self, workspace: Workspace):
        self._workspace = workspace

    @property
    def token(self):
        """ API token used to call endpoint (optional) """
        return self.get_attribute("token")

    @property
    def endpoint(self):
        """ Endpoint used to call analitico APIs """
        return self.get_attribute("endpoint")

    ##
    ## Internal Utilities
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
        self.warning("get_item_type - couldn't find type for: " + item_id)
        return None

    def get_url_headers(self, url: str) -> (str, dict):
        # If the url uses the analitico:// scheme for assets stored on the cloud
        # service, it will convert the url to a regular https:// scheme.
        # If the url points to an analitico API call, the request will have the
        # ?token= authorization token header added to it.
        # temporarily while all internal urls are updated to analitico://
        assert isinstance(url, str)
        # see if assets uses analitico://workspaces/... scheme
        if url.startswith("analitico://"):
            if not self.endpoint:
                msg = f"Analitico SDK is not configured with a valid API endpoint and cannot get {url}"
                raise AnaliticoException(msg)
            url = self.endpoint + url[len("analitico://") :]

        try:
            url_parse = urllib.parse.urlparse(url)
        except Exception:
            pass
        headers = {}
        if url_parse and url_parse.scheme in ("http", "https"):
            hostname = url_parse.hostname
            is_analitico = hostname and ("analitico.ai" in hostname or "127.0.0.1" in hostname)
            if is_analitico and self.token:
                # if url is connecting to analitico.ai add token
                headers = {"Authorization": "Bearer " + self.token}
        return url, headers

    def get_url_stream(
        self,
        url: str,
        data: dict = None,
        json: dict = None,
        files: dict = None,
        binary: bool = False,
        cache: bool = True,
        method: str = "GET",
        status_code: int = 200,
        chunk_size: int = 1024 * 1024,
    ):
        """
        Returns a stream to the given url. This works for regular http:// or https://
        and also works for analitico:// assets which are converted to calls to the given
        endpoint with proper authorization tokens. The stream is returned as an iterator.
        """
        # we should not take the raw response stream here as it could be gzipped or encoded.
        # we take the decoded content as a text string and turn it into a stream or we take the
        # decompressed binary content and also turn it into a stream.
        url, headers = self.get_url_headers(url)
        response = requests.request(method, url, data=data, files=files, stream=True, headers=headers)
        if status_code and response.status_code != status_code:
            msg = f"The response from {url} should have been {status_code} but instead it is {response.status_code}."
            raise AnaliticoException(msg)
        # always treat content as binary, utf-8 encoding is done by readers
        if binary:
            for chunk in response.iter_content(chunk_size):
                yield chunk
        else:
            for chunk in response.iter_content(chunk_size):
                yield chunk

    def get_url_json(self, url: str, json: dict = None, method: str = "GET", status_code: int = 200) -> dict:
        """
        Get a json response from given url. If the url starts with analitico:// it will be
        substituted with the url of the actual endpoint for analitico.ai and a bearer token
        will be attached for authorization.
        
        Arguments:
            url {str} -- An absolute url to be read or an analitico:// url for API calls.
            data {dict} -- An optional dictionary that should be sent (eg: for POST calls).
        
        Keyword Arguments:
            method {str} -- HTTP method to be used (default: {"get"})
        
        Returns:
            dict -- The json response.
        """
        url, headers = self.get_url_headers(url)

        response = requests.request(method, url, headers=headers, json=json)
        if status_code and response.status_code != status_code:
            msg = f"The response from {url} should have been {status_code} but instead it is {response.status_code}."
            raise AnaliticoException(msg)
        try:
            return response.json()
        except Exception:
            return None

    ##
    ## with Factory as: lifecycle methods
    ##

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """ Leave any temporary files upon exiting """
        pass

    ##
    ## SDK v1 methods
    ##

    def create_item(self, item_type: str, workspace: Workspace = None, **kwargs) -> Item:
        if not workspace:
            workspace = self.get_workspace()

        data = {"data": kwargs}
        data["data"]["workspace_id"] = workspace.id
        if "type" in kwargs:
            kwargs.pop("type")
        if "id" in kwargs:
            data["id"] = kwargs.pop("id")

        json = self.get_url_json(f"analitico://{item_type}s", json=data, method="POST", status_code=201)
        assert "data" in json
        return analitico.models.models_factory(self, json["data"])

    def create_dataset(self, workspace: Workspace = None, **kwargs) -> Dataset:
        return self.create_item(workspace=workspace, item_type=analitico.DATASET_TYPE, **kwargs)

    def create_recipe(self, workspace: Workspace = None, **kwargs) -> Recipe:
        return self.create_item(workspace=workspace, item_type=analitico.RECIPE_TYPE, **kwargs)

    def create_notebook(self, workspace: Workspace = None, **kwargs) -> Notebook:
        return self.create_item(workspace=workspace, item_type=analitico.NOTEBOOK_TYPE, **kwargs)

    ##
    ## Retrieve specific items by id
    ##

    def get_items(self, item_type: str) -> Item:
        """ Retrieves item from the server by item_id """
        json = self.get_url_json(f"analitico://{item_type}s")
        items = []
        for item_data in json["data"]:
            items.append(analitico.models.models_factory(self, item_data))
        return items

    def get_item(self, item_id: str) -> Item:
        """ Retrieves item from the server by item_id """
        json = self.get_url_json(f"analitico://{self.get_item_type(item_id)}s/{item_id}")
        assert "data" in json
        return analitico.models.models_factory(self, json["data"])

    def get_workspace(self, workspace_id: str = None) -> Workspace:
        """
        Returns the workspace with the given id (or the default workspace).

        Keyword Arguments:
            workspace_id {str} -- The id of the workspace to be retrieve, eg. ws_xxx (default: {None})

        Returns:
            Workspace -- A Workspace object that can be used to retrieve files or other items.
        """
        if not workspace_id:
            if not self.workspace:
                workspaces = self.get_items(analitico.WORKSPACE_TYPE)
                if len(workspaces) != 1:
                    raise AnaliticoException("You do not have a default workspace, please assign sdk.workspace")
                self.workspace = workspaces[0]
            return self.workspace

        workspace = self.get_item(workspace_id)
        assert isinstance(workspace, Workspace)
        return workspace

    def get_dataset(self, dataset_id) -> Dataset:
        dataset = self.get_item(dataset_id)
        assert isinstance(dataset, Dataset)
        return dataset

    def get_recipe(self, recipe_id) -> Recipe:
        recipe = self.get_item(recipe_id)
        assert isinstance(recipe, Recipe)
        return recipe

    def get_notebook(self, notebook_id) -> Notebook:
        notebook = self.get_item(notebook_id)
        assert isinstance(notebook, Notebook)
        return notebook
