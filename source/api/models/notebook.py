import collections
import jsonfield
import os
import os.path
import papermill
import json

import nbformat
from nbconvert import HTMLExporter

from django.db import models
from django.utils.crypto import get_random_string

import analitico
import analitico.plugin
import analitico.utilities

from analitico import IFactory
from analitico.utilities import save_json, read_json, get_dict_dot

from .job import Job
from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace

NOTEBOOK_MIME_TYPE = "application/x-ipynb+json"

##
## Notebook - django model used to represents Jupyter notebooks in analitico
## https://nbformat.readthedocs.io/en/latest/format_description.html#
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
        nb_run(job, factory, notebook_item=self, upload=True)


##
## Utilities
##


def nb_run(job: Job, factory: IFactory, notebook_item, notebook_name=None, upload=False, tags=None, **kwargs):
    """ 
    Runs a Jupyter notebook with given job, factory, notebook and optional item to upload assets to 
    
    Parameters:
    job (Job): The job context that the notebook should be processed in
    factory (IFactory): Factory to be using for resources, loggins, disk, etc.
    notebook_item: Server model from which the notebook is retrieved
    notebook_name: Name of notebook to be used (None for default notebook)
    upload: True if artifacts produced while processing the notebook should be updated to the notebook_item (optional)
    tags: A comma separated list of tags used to filter notebook, see: nb_filter_tags (optional)
    
    Returns:
    The processed notebook
    """
    try:
        notebook = notebook_item.get_notebook(notebook_name)
        if not notebook:
            factory.warning("Running an empty notebook %s", notebook_item.id)
            return

        # save notebook to file
        artifacts_path = factory.get_artifacts_directory()
        notebook_path = os.path.join(artifacts_path, "notebook.ipynb")
        notebook_out_path = os.path.join(artifacts_path, "notebook.output.ipynb")
        save_json(notebook, notebook_path)

        # run notebook and save output to separate file
        action = job.action if job else None
        action = "train"

        papermill.execute_notebook(
            notebook_path,
            notebook_out_path,
            parameters=dict(action=action, name="gionata"),
            cwd=artifacts_path,  # any artifacts will be created in cwd
        )

        notebook = read_json(notebook_out_path)

        if upload:
            # upload processed artifacts to /data
            os.remove(notebook_path)
            os.remove(notebook_out_path)
            factory.upload_artifacts(notebook_item)

        # save executed notebook
        notebook_item.set_notebook(notebook, notebook_name)
        notebook_item.save()

        return notebook

    except Exception as exc:
        factory.exception("Exception while running notebook %s", notebook_item.id, item=notebook_item, job=job)


def nb_filter_tags(notebook: dict, tags=None):
    """ Returns a notebook that has only those cells marked with the given tags """
    if isinstance(tags, str):
        tags = tags.split(",")
    if not isinstance(tags, list) or len(tags) < 1:
        return notebook

    copy = notebook.copy()
    copy["cells"] = []
    for cell in notebook["cells"]:
        cell_tags = get_dict_dot(cell, "metadata.tags", None)
        if cell_tags and any(tag in cell_tags for tag in tags):
            copy["cells"].append(cell)
    return copy


def nb_convert_to_html(notebook: dict, template="full"):
    """ Convert a Jupyter notebook to HTML and return as string """
    # uses jupyter nbconvert as a library
    # https://nbconvert.readthedocs.io/en/5.x/nbconvert_library.html

    # kind of a long trip, we serialize again because nbconvert takes a string...
    notebook_json = json.dumps(notebook)
    notebook_obj = nbformat.reads(notebook_json, as_version=4)

    html_exporter = HTMLExporter()
    html_exporter.template_file = template  # eg: basic, full, etc...
    (body, resources) = html_exporter.from_notebook_node(notebook_obj)
    return body, resources
