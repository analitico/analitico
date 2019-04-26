import collections
import jsonfield
import os
import json

from django.db import models
from django.utils.crypto import get_random_string
from django.db import transaction

import analitico
import analitico.plugin
import analitico.utilities

from analitico import AnaliticoException
from analitico.factory import Factory
from analitico.schema import generate_schema
from analitico.utilities import read_json, read_text
from analitico.pandas import pd_read_csv

from .items import ItemMixin, ItemAssetsMixin, ASSETS_CLASS_DATA
from .workspace import Workspace
from .notebook import nb_run, nb_replace, nb_find_cells, nb_replace_source
from .token import get_workspace_token

##
## Dataset
##


def generate_dataset_id():
    return analitico.DATASET_PREFIX + get_random_string()


class Dataset(ItemMixin, ItemAssetsMixin, models.Model):
    """ A dataset contains a data source description, its metadata and its data """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_dataset_id)

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Description (markdown supported)
    description = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    # A Jupyter notebook https://nbformat.readthedocs.io/en/latest/
    notebook = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Jobs
    ##

    def run(self, job, factory: Factory, **kwargs):
        """ Run job actions on the dataset """
        try:
            # process action runs plugin to generate and save data.csv and its schema
            if job.action == "dataset/process":

                # TODO remove this line after June 2019
                # pluging are no longer used in datasets and can be removed
                # this code can be removed once all datasets have been cleared
                self.set_attribute("plugin", None)

                # if dataset has a notebook it will be used to process
                notebook = self.get_notebook()

                if notebook:
                    nb_run(notebook_item=self, notebook_name=None, factory=factory, upload=True, save=True)
                    return

                # if the dataset doesn't have a notebook we can initialize it with a template
                # which initially will contain a plugin to read the source data from csv and apply a schema
                # and may later on be extended to do other data transformations tasks

                # look for .csv assets
                asset_url = None
                if self.assets:
                    for asset in self.assets:
                        if asset.get("content_type") == "text/csv" or asset["path"].endswith(".csv"):
                            asset_url = asset["url"]

                if not asset_url:
                    raise AnaliticoException(
                        "You should upload a .csv file to " + self.id + " before processing it.", item=self
                    )

                # retrieve initial schema for file asset
                asset_stream = factory.get_url_stream(asset_url, binary=False)
                asset_df = pd_read_csv(asset_stream)  # TODO read a maximum of X rows to infer schema
                asset_schema = generate_schema(asset_df)
                asset_schema = json.dumps(asset_schema)  # pretty? indent=4

                # read notebook template
                notebook_filename = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), "assets/dataset-csv-template.ipynb"
                )
                notebook = read_json(notebook_filename)

                # TODO generic url for csv file instead of specific filename

                # inject token, source and schema in template cells
                token = get_workspace_token(self.workspace)
                nb_replace_source(notebook, tags="token", source='token = "{}"'.format(token))
                nb_replace_source(notebook, tags="dataset_url", source='dataset_url = "{}"'.format(asset_url))
                nb_replace_source(notebook, tags="dataset_schema", source="dataset_schema = " + asset_schema)

                self.notebook = notebook
                self.save()

                # TODO pass token as a parameter, create token if needed
                # run notebook and save it in item with updated info
                nb_run(notebook_item=self, notebook_name=None, factory=factory, upload=True, save=True)

            self.save()
        except Exception as exc:
            raise exc
