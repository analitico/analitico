import collections
import jsonfield
import tempfile
import pandas as pd
import os
import os.path

from django.contrib.auth.models import Group
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from rest_framework.exceptions import APIException

import analitico
import analitico.plugin
import analitico.utilities

from analitico.utilities import get_dict_dot, set_dict_dot, logger
from analitico.schema import generate_schema

from .user import User
from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace

##
## Dataset
##

DATASET_PREFIX = "ds_"  # dataset source, filters, etc


def generate_dataset_id():
    return DATASET_PREFIX + get_random_string()


class Dataset(ItemMixin, ItemAssetsMixin, models.Model):
    """ A dataset contains a data source description, its metadata and its data """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_dataset_id, verbose_name=_("Id"))

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True, verbose_name=_("Title"))

    # Description (markdown supported)
    description = models.TextField(blank=True, verbose_name=_("Description"))

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created"))

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated"))

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(
        load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True, verbose_name=_("Attributes")
    )

    ##
    ## Jobs
    ##

    def run(self, job, runner, **kwargs):
        """ Run job actions on the dataset """
        try:
            # process action runs plugin to generate and save data.csv and its schema
            if job.action == "dataset/process":
                plugin_settings = self.get_attribute("plugin")
                new_plugin = False

                # if the dataset doesn't have a plugin we can initialize it with a dataset pipeline
                # which initially will contain a single plugin to read the source data from csv
                # and may later on be extended to do other data transformations tasks
                if not plugin_settings and self.assets:
                    for asset in self.assets:
                        if asset.get("content_type") == "text/csv" or asset["path"].endswith(".csv"):
                            plugin_settings = {
                                "type": analitico.plugin.PLUGIN_TYPE,
                                "name": analitico.plugin.DATAFRAME_PIPELINE_PLUGIN,
                                "plugins": [
                                    {
                                        "type": analitico.plugin.PLUGIN_TYPE,
                                        "name": analitico.plugin.CSV_DATAFRAME_SOURCE_PLUGIN,
                                        "source": {"content_type": "text/csv", "url": asset["path"]},
                                    }
                                ],
                            }
                            new_plugin = True
                            self.set_attribute("plugin", plugin_settings)
                            self.save()
                            break

                if plugin_settings:
                    plugin = runner.create_plugin(**plugin_settings)
                    # plugin will produce pandas dataframe and create data.csv, data.csv.info
                    df = plugin.run()
                    if new_plugin:
                        # apply derived schema as a starting schema which
                        # users will then customize and change, etc.
                        schema = generate_schema(df)
                        with transaction.atomic():
                            self.refresh_from_db()
                            plugin_settings = self.get_attribute("plugin")
                            plugin_settings["plugins"][0]["source"]["schema"] = schema
                            self.set_attribute("plugin", plugin_settings)
                            self.save()
                    # upload processing artifacts to /data
                    runner.upload_artifacts(self)
            self.save()
        except Exception as exc:
            raise exc
