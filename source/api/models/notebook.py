import collections
import jsonfield
import os
import os.path
import papermill
import json
import datetime
import nbformat
import subprocess
from subprocess import PIPE

from nbconvert import HTMLExporter

from django.db import models
from django.utils.crypto import get_random_string

from papermill.iorw import load_notebook_node, write_ipynb, local_file_io_cwd
from papermill.utils import chdir
from papermill.execute import prepare_notebook_metadata, parameterize_notebook

import analitico
import analitico.plugin
import analitico.utilities

from analitico.factory import Factory
from analitico.utilities import save_json, read_json, get_dict_dot, time_ms, subprocess_run
from analitico.exceptions import AnaliticoException

from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace

import logging

logger = logging.getLogger("analitico")

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

    def run(self, job, factory: Factory, **kwargs):
        """ Run notebook, update it, upload artifacts """
        # TODO should we really upload artifacts or not?
        nb_run(notebook_item=self, factory=factory, upload=True, save=True, tags=None, job=job)


##
## Utilities
##


def nb_run(
    notebook_item, notebook_name=None, parameters=None, tags=None, factory=None, upload=False, save=True, job=None
):
    """ 
    Runs a Jupyter notebook with given parameters, factory, notebook and optional item to upload assets to 
    
    Parameters:
    notebook_item: Server model from which the notebook is retrieved
    notebook_name: Name of notebook to be used (None for default notebook)
    tags: A comma separated list of tags used to filter notebook, see: nb_filter_tags (optional)
    factory (Factory): Factory to be using for resources, loggins, disk, etc.
    upload: True if artifacts produced while processing the notebook should be updated to the notebook_item (optional)
    save: True if the executed notebook should be saved back into the model (default: false)
    job: If a Job is passed than the output will be captured and added to the job itself. 

    Returns:
    The processed notebook
    """
    assert factory
    notebook = notebook_item.get_notebook(notebook_name)
    if not notebook:
        factory.warning("Running an empty notebook %s", notebook_item.id)
        return notebook

    # remove cells with error warnings from previous runs
    notebook = nb_clear_error_cells(notebook)

    if tags:
        notebook = nb_filter_tags(notebook, tags)

    # save notebook to file
    artifacts_path = factory.get_artifacts_directory()
    notebook_path = os.path.join(artifacts_path, "notebook.ipynb")
    notebook_out_path = os.path.join(artifacts_path, "notebook.output.ipynb")
    save_json(notebook, notebook_path)
    assert os.path.isfile(notebook_path)

    # extract scripts used to install dependencies, etc.
    notebook_setup_path = os.path.join(artifacts_path, "notebook.setup.sh")
    nb_extract_setup_script(notebook, notebook_setup_path)

    parameters = parameters if parameters else {}
    parameters["action"] = factory.job.action if factory.job else "process"

    try:
        # use containerized papermill
        use_papermill_docker = True

        if use_papermill_docker:
            cmd = os.environ.get("ANALITICO_PAPERMILL_DOCKER_SCRIPT", None)
            if not cmd:
                logger.warning("ANALITICO_PAPERMILL_DOCKER_SCRIPT is not configured is a SECURITY RISK!!!")
                cmd = "papermill"

            # run papermill via command line. this allows us to run a script which will create
            # a docker where we can run the notebook via papermill with untrusted content without
            # having the security issues we would otherwise have in our main environment (eg. env variables, etc)
            args = [cmd, notebook_path, notebook_out_path, "--cwd", artifacts_path, "--log-output"]
            for key, value in parameters.items():
                args.append("-p")
                args.append(key)
                args.append(value)

            subprocess_run(args, cwd=artifacts_path, job=job)
            notebook = read_json(notebook_out_path)

        else:
            # SECURITY WARNING: if we run papermill here via its direct api it will run in our
            # same environment. this means that the code in our notebooks can have access to environment
            # variables potentially containing sensitive keys, etc. if the notebooks are not trusted,
            # papermill should run inside a docker which will provide insulation
            notebook = papermill.execute_notebook(
                notebook_path,
                notebook_out_path,
                parameters=parameters,
                cwd=artifacts_path,  # any artifacts will be created in cwd
            )

    except Exception as exc:
        evalue = str(exc)
        try:
            notebook = read_json(notebook_out_path)

            if save:
                notebook_item.set_notebook(notebook, notebook_name)
                notebook_item.save()

            errors = nb_get_errors(notebook)
            if len(errors) > 0:
                evalue = errors[0]["evalue"]
                if job:
                    job.set_attribute("errors", errors)
        except Exception:
            pass
        raise analitico.AnaliticoException(
            f"An error occoured while running {notebook_item.id}: {evalue}", item=notebook_item, job=job
        ) from exc

    if upload:
        # upload processed artifacts to /data
        os.remove(notebook_path)
        os.remove(notebook_out_path)
        factory.upload_artifacts(notebook_item)

    if save:
        # save executed notebook
        # TODO maybe we need to reload item model in case notebook itself altered it?
        notebook_item.set_notebook(notebook, notebook_name)
        notebook_item.save()
    return notebook


def nb_get_errors(notebook: dict):
    """ Scans the notebook and returns any and all error outputs """
    # https://nbformat.readthedocs.io/en/latest/format_description.html#error
    errors = []
    for cell in notebook.get("cells", []):
        for idx, output in enumerate(cell.get("outputs", [])):
            if output.get("output_type", None) == "error":
                error = output.copy()
                error["cell_index"] = idx
                errors.append(error)
    return errors


def nb_find_cells(notebook: dict, tags: str) -> list:
    """ Returns a list of cells containing all the requested tags (passed as list or comma separated) """
    if isinstance(tags, str):
        tags = tags.split(",")
    if not isinstance(tags, list) or len(tags) < 1:
        return list()

    cells = []
    for cell in notebook["cells"]:
        cell_tags = get_dict_dot(cell, "metadata.tags", None)
        if cell_tags and all(tag in cell_tags for tag in tags):
            cells.append(cell)
    return cells


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


def nb_extract_source(nb, disable_scripts=True):
    """ Extract source code from notebook, optionally disabling lines starting with ! and % that run scripts and special modes """
    source = ""
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code":
            if disable_scripts:
                # TODO could write exception blocks cell by cell and use them to improve error messaging

                source += "# Cell {}\n".format(i)
                for line in iter(cell["source"].splitlines()):
                    # lines starting with ! and % are special scripts and are removed
                    if len(line) > 0 and line[0] in ("!", "%"):
                        source += "# COMMENTED OUT: "
                    source += line + "\n"
            else:
                # comment with cell number makes it a bit easier in case of exceptions
                source += "# Cell {}\n{}\n\n".format(i, cell["source"])
    return source


def nb_replace(notebook: dict, find: str, replace: str, source=True) -> dict:
    """ Replace given strings in notebook's source code """

    # replace values in source code
    if source:
        if "cells" in notebook:
            for cell in notebook["cells"]:
                if "source" in cell:
                    cell["source"] = [line.replace(find, replace) for line in cell["source"]]

    # TODO replace in metadata, etc

    return notebook


def nb_replace_source(notebook: dict, tags, source):
    """ Find cells with given tags and replace source with given source code lines """
    if source is str:
        source = [source]
    tagged_cells = nb_find_cells(notebook, tags=tags)
    for tagged_cell in tagged_cells:
        tagged_cell["source"] = source
    return notebook


def nb_clear_error_cells(notebook: dict) -> dict:
    """ Removes any cells that were created by previous papermill runs showing notebook execution errors """
    try:
        while len(notebook["cells"]) > 1:
            # error cells created by papermill are not marked explicitely as such, so we just check
            # the first cells to see if they have the characteristics of papermill error cells and in
            # that case we remove them from the notebook...
            cell = notebook["cells"][0]
            if (
                cell["cell_type"] == "code"
                and cell["execution_count"] == None
                and cell["metadata"]["hide_input"]
                and cell["metadata"]["inputHidden"]
                and "An Exception was encountered at" in "".join(cell["outputs"][0]["data"]["text/html"])
            ):
                notebook["cells"].remove(cell)
            else:
                return notebook
    except KeyError:
        # cells or keys we looked for are missing, ignore and proceed
        pass
    return notebook


# for now we take cells with a variety of tags, we'll restrict later once we decide on naming
NB_SERVERLESS_TAGS = ["serverless", "handle", "predict", "prediction"]


def nb_extract_serverless(nb: dict) -> (str, str):
    """ Extract source code and scripts from notebook for docker packaging """
    source, script = "", ""

    # scan all cells in the notebook but consider only code cells
    for i, cell in enumerate(nb["cells"]):
        tags = get_dict_dot(cell, "metadata.tags", None)
        tags_msg = ", ".join(tags) if tags else "none"
        source += "\n\n# cell: {}, type: {}, tags: {}\n".format(i + 1, cell["cell_type"], tags_msg)

        if cell["cell_type"] != "code":
            source += "# skipped cell\n"
        else:
            # make sure lines contains individual lines, notebooks sometimes
            # have a single string of multiple lines and sometimes have an array of lines
            lines = cell["source"]
            if isinstance(lines, list):
                lines = "".join(lines)
            lines = lines.splitlines()

            # is cell tagged or does it contain handle method? if so, include its source
            is_serverless_cell = tags and any(tag in NB_SERVERLESS_TAGS for tag in tags)
            if not is_serverless_cell:
                is_serverless_cell = any(line.startswith("def handle(") for line in lines)

            if not is_serverless_cell:
                source += "# skipped code\n"
            else:
                for j, line in enumerate(lines):
                    if len(line) > 0 and line[0] in ("!", "%"):
                        # command that should be passed to setup script?
                        script += f"# cell: {i+1}, line: {j+1}\n{line[1:]}\n\n"
                    else:
                        source += line + "\n"

    return source, script


def nb_extract_setup_script(nb: dict, setup_path):
    """ Extract setup scripts from notebook for docker packaging. Takes all ! and % source lines and writes them out to setup_path. """
    with open(setup_path, "w") as f:
        f.write("# notebook setup script\n\n")

        # scan all cells in the notebook but consider only code cells
        for i, cell in enumerate(nb["cells"]):
            if cell["cell_type"] == "code":
                # make sure lines contains individual lines, notebooks sometimes
                # have a single string of multiple lines and sometimes have an array of lines
                lines = cell["source"]
                if isinstance(lines, list):
                    lines = "".join(lines)
                lines = lines.splitlines()

                for j, line in enumerate(lines):
                    # extract ! lines for scripts, no % magic lines
                    if len(line) > 0 and line[0] == "!": 
                        # command that should be passed to setup script
                        f.write(f"# cell: {i+1}, line: {j+1}\n{line[1:]}\n\n")
