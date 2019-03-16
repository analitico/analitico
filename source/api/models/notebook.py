import collections
import jsonfield
import os
import os.path
import papermill

from django.db import models
from django.utils.crypto import get_random_string

import analitico
import analitico.plugin
import analitico.utilities

from analitico import IFactory
from analitico.utilities import save_json, read_json

from .job import Job
from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace

##
## Notebook
##


def generate_notebook_id():
    return analitico.NOTEBOOK_PREFIX + get_random_string()


class Notebook(ItemMixin, ItemAssetsMixin, models.Model):
    """ A Jupyter notebook with its data and metadata """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_notebook_id)

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

    # The notebook itself in Jupyter notebook format
    # https://nbformat.readthedocs.io/en/latest/
    notebook = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Jobs
    ##

    def run(self, job, factory: IFactory, **kwargs):
        """ Run notebook, update it, upload artifacts """
        nb_run(job, factory, self, self)

##
## Utilities
##


def nb_run(job: Job, factory: IFactory, notebook: Notebook, upload_to=None, **kwargs):
    """ Runs a Jupyter notebook with given job, factory, notebook and optional item to upload assets to """
    try:
        if not notebook.notebook:
            factory.warning("Running an empty notebook %s", notebook.id)
            return

        # save notebook to file
        artifacts_path = factory.get_artifacts_directory()
        notebook_path = os.path.join(artifacts_path, "notebook.ipynb")
        notebook_out_path = os.path.join(artifacts_path, "notebook-output.ipynb")
        save_json(notebook.notebook, notebook_path)

        # run notebook and save output to separate file
        action = job.action if job else None
        papermill.execute_notebook(
            notebook_path,
            notebook_out_path,
            parameters=dict(action=action, name="gionata"),
            cwd=artifacts_path,  # any artifacts will be created in cwd
        )

        # save executed notebook
        notebook.notebook = read_json(notebook_out_path)
        notebook.save()

        # upload processed artifacts to /data
        if upload_to:
            os.remove(notebook_path)
            os.remove(notebook_out_path)
            factory.upload_artifacts(upload_to)
        notebook.save()

    except Exception as exc:
        factory.exception("Exception while running notebook %s", notebook.id, item=upload_to, notebook=notebook, job=job)
