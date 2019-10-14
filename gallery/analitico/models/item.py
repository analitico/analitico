import os
import pandas as pd
import tempfile
import urllib
import requests
import base64
import io

from analitico import AnaliticoException, logger
from analitico.mixin import AttributeMixin
from analitico.utilities import save_text, subprocess_run, get_dict_dot
from analitico.constants import CSV_SUFFIXES, PARQUET_SUFFIXES
from analitico.pandas import pd_read_csv

from collections import OrderedDict
from pathlib import Path

DF_SUPPORTED_FORMATS = (".parquet", ".csv")


class Item(AttributeMixin):
    """ Base class for items like datasets, recipes and notebooks on Analitico. """

    # SDK used to communicate with the service
    sdk = None

    def __init__(self, sdk, item_data: dict):
        # item's basics
        assert sdk
        self.sdk = sdk
        self.id = item_data["id"]
        self.type = item_data["type"].replace("analitico/", "")
        # big bag of open ended properties to be retrieved via get_attribute
        super().__init__(**item_data["attributes"])

    ##
    ## Properties
    ##

    @property
    def title(self) -> str:
        """ The title of this item. """
        return self.get_attribute("title")

    @title.setter
    def title(self, title: str):
        """ Set the title of this item. """
        self.set_attribute("title", title)

    @property
    def url(self):
        """ Url of this item on the service. """
        item_url = f"analitico://{self.sdk.get_item_type(self.id)}s/{self.id}"
        item_url, _ = self.sdk.get_url_headers(item_url)
        return item_url

    @property
    def workspace(self):
        """ Returns the workspace that owns this item (or None if this is a workspace). """
        if self.type == "workspace":
            return self
        workspace_id = self.get_attribute("workspace_id")
        return self.sdk.get_workspace(workspace_id) if workspace_id else None

    ##
    ## Internals
    ##

    def _upload_directly_to_storage(self, filepath: str = None, remotepath: str = None) -> bool:
        """
        Upload a file directly to storage using webdav. This puts less load on the server
        for larger uploads but has a few drawbacks including not generating automatic triggers
        on the service, notifications, etc.
        """
        workspace = self.workspace
        if workspace:
            storage = workspace.get_attribute("storage")
            if "webdav" in storage.get("driver"):
                # storage configuration for this workspace
                server = storage["url"]
                user = get_dict_dot(storage, "credentials.username")
                password = get_dict_dot(storage, "credentials.password")

                remotepath = f"{self.type}s/{self.id}/{remotepath}"

                with open(filepath, "rb") as f:
                    # direct upload implies the containing directory already exists
                    url = f"{server}/{remotepath}"
                    response = requests.put(url, data=f, auth=(user, password))
                    if response.status_code in (200, 201, 204):
                        return True

                # probably missing the directory
                if response.status_code == 403:
                    parts = remotepath.split("/")[:-1]
                    parts_url = server + "/"
                    for part in parts:
                        parts_url += part + "/"
                        response = requests.request("MKCOL", parts_url, auth=(user, password))
                        if response.status_code not in (405, 200, 201, 204):
                            msg = f"An error occoured while creating directory {parts_url}"
                            raise AnaliticoException(msg, status_code=response.status_code)

                    # now we can retry uploading the file as we know for sure its directory exists
                    with open(filepath, "rb") as f:
                        response = requests.put(url, data=f, auth=(user, password))
                        if response.status_code in (200, 201, 204):
                            return True

                msg = f"An error occoured while uploading {url}"
                raise AnaliticoException(msg, status_code=response.status_code)
        return False

    ##
    ## Methods
    ##

    def upload(
        self, filepath: str = None, df: pd.DataFrame = None, remotepath: str = None, direct: bool = True
    ) -> bool:
        """
        Upload a file to the storage drive associated with this item. You can upload a file by indicating its
        filepath on the local disk or by handing a Pandas dataframe which is automatically saved to a file and
        then uploaded.
        
        Keyword Arguments:
            filepath {str} -- Local filepath (or None if passing a dataframe)
            df {pd.DataFrame} -- A dataframe that should be saved and uploaded (or None if passing a filepath)
            remotepath {str} -- Path on remote driver, eg: file.txt, datasets/customers.csv, etc...
            direct {bool} -- False if loaded via analitico APIs, true if loaded directly to storage.
        
        Returns:
            bool -- True if the file was uploaded or an Exception explaining the problem.
        """
        if isinstance(df, pd.DataFrame):
            if not remotepath:
                remotepath = filepath if filepath else "data.parquet"

            # encode dataframe to disk temporarily
            suffix = Path(remotepath).suffix
            with tempfile.NamedTemporaryFile(mode="w+", prefix="df_", suffix=suffix) as f:
                if suffix in PARQUET_SUFFIXES:
                    df.to_parquet(f.name)
                elif suffix in CSV_SUFFIXES:
                    df.to_csv(f.name)
                else:
                    msg = f"{remotepath} is not in a supported format."
                    raise AnaliticoException(msg, status_code=400)
                return self.upload(filepath=f.name, remotepath=remotepath)

        # uploading a single file?
        if os.path.isfile(filepath):
            if not remotepath:
                remotepath = Path(filepath).name

            # no absolute paths
            assert not remotepath.startswith("/"), "remotepath should be relative, eg: flower.jpg or flowers/flower.jpg"

            if direct:
                try:
                    # see if we can upload directly to storage
                    if self._upload_directly_to_storage(filepath, remotepath):
                        return True
                except AnaliticoException as exc:
                    logger.error(f"upload - direct to storage failed, will try via /files APIs, exc: {exc}")

            url = self.url + "/files/" + remotepath
            url, headers = self.sdk.get_url_headers(url)

            with open(filepath, "rb") as f:
                # multipart encoded upload
                response = requests.put(url, files={"file": f}, headers=headers)

                # raw upload
                # response = requests.put(url, data=f, headers=headers)

                if response.status_code not in (200, 204):
                    msg = f"Could not upload {filepath} to {url}, status: {response.status_code}"
                    raise AnaliticoException(msg, status_code=response.status_code)
                return True

        raise NotImplementedError("Uploading multiple files at once is not yet implemented.")

    def download(
        self, remotepath: str, filepath: str = None, stream: bool = False, binary: bool = True, df: str = None
    ):
        """
        Downloads the file asset associated with this item to a file, stream or dataframe.
        
        Arguments:
            remotepath {str} -- The path of the file asset, eg. data.csv

        Keyword Arguments:
            filepath {str} -- The file path where this asset should be saved, or None.
            stream {bool} -- True if file should be returned as a stream.
            df {bool} -- True if file should be returned as pandas dataframe.
            binary {bool} -- True for binary downloads, false for text. (default: {True})

        Returns:
            The download stream or dataframe or nothing if saved to file.
        """
        url = self.url + "/files/" + remotepath
        url_stream = self.sdk.get_url_stream(url, binary=binary)
        # TODO if we're running serverless or in jupyter the assets may already be on a locally mounted drive (optimize)

        if stream:
            return url_stream

        if filepath:
            with open(filepath, "w+b") as f:
                for chunk in iter(url_stream):
                    f.write(chunk)

        if df:
            suffix = Path(remotepath).suffix
            with tempfile.NamedTemporaryFile(prefix="df_", suffix=suffix) as f:
                for chunk in iter(url_stream):
                    f.write(chunk)
                if suffix in CSV_SUFFIXES:
                    return pd_read_csv(f.name)
                elif suffix in PARQUET_SUFFIXES:
                    return pd.read_parquet(f.name)
                else:
                    msg = f"Can't read {df} to a pandas dataframe, please load .csv or .parquet files."
                    raise AnaliticoException(msg, status_code=400)

    def save(self) -> bool:
        """ Save any changes to the service. """
        json = self.sdk.get_url_json(self.url, method="PUT", json=self.to_dict(), status_code=200)
        self.attributes = json["data"]["attributes"]
        return True

    def delete(self) -> bool:
        """
        Delete this item from the service.
        
        Returns:
            bool -- True if item was deleted.
        """
        self.sdk.get_url_json(self.url, method="DELETE", status_code=204)
        return True

    def to_dict(self) -> dict:
        """ Return item as a dictionary. """
        return {"id": self.id, "type": "analitico/" + self.type, "attributes": self.attributes}

    def __str__(self):
        return self.type + ": " + self.id
