##
# Script executed for running a notebook by the job run
##

import logging
import os
import json
import argparse
import requests
import tempfile
import datetime
import sys

import papermill
from papermill.execute import load_notebook_node, write_ipynb
import nbformat

from analitico import AnaliticoException, ACTION_RUN, ACTION_RUN_AND_BUILD
from analitico.utilities import read_json, save_json, subprocess_run, read_text, save_text

import analitico.logging

# python libraries search path
sys.path.append(os.getenv("ANALITICO_ITEM_PATH", ""))

# provide a basic command line interface to launch jobs
parser = argparse.ArgumentParser(description="Process a job.")
parser.add_argument(
    "notebooks", metavar="N", type=str, nargs="+", default="notebook.ipynb", help="a notebook file to be processed"
)
args = parser.parse_args()

# setup logging so that we replace python's root logger with a new handler that
# can format messages as json in a way that is easily readable by our fluentd
# while preserving the log messages' metadata (eg. level, function, line, logger, etc)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": analitico.logging.FluentdFormatter, "format": "%(asctime)s %(message)s"}},
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stderr",
        }
    },
    "root": {"handlers": ["default"]},
}
logging.config.dictConfig(LOGGING_CONFIG)


def try_request_notification(notification_url):
    try:
        requests.get(notification_url)
        logging.info("Notification requested")
    except Exception:
        logging.warning("Failed to request the notification", exec_info=True)


# TODO: Refactory required. This method is duplicated from api/models/notebook.py. Methods
#       from notebook.py should not be used anywhere else because job runs are executed only by this script.
def nb_extract_source(nb, disable_scripts=True):
    """ Extract source code from notebook, optionally disabling lines starting with ! and % that run scripts and special modes """
    source = ""
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code":
            if disable_scripts:
                # TODO could write exception blocks cell by cell and use them to improve error messaging

                source += "# Cell {}\n".format(i)
                for line in iter(cell["source"]):
                    # lines starting with ! and % are special scripts and are removed
                    if len(line) > 0 and line[0] in ("!", "%"):
                        source += "# COMMENTED OUT: "
                    source += line + "\n"
            else:
                # comment with cell number makes it a bit easier in case of exceptions
                source += "# Cell {}\n{}\n\n".format(i, cell["source"])
    return source


# TODO: Refactory required. This method is duplicated from api/models/notebook.py. Methods
#       from notebook.py should not be used anywhere else because job runs are executed only by this script.
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


def add_bless_cell(notebook_node):
    """ 
    User can customize the logic used to decide if a model is imporoved
    than the precedent. The logic is defined in the method `bless()`
    inside the notebook.py module of the recipe.

    Add the invokation of the bless() function in the notebook itself
    as last code cell.
    """
    blessed_model_id = os.getenv("ANALITICO_BLESSED_MODEL_ID")
    blessed_metrics = {}
    if blessed_model_id:
        blessed_metadata_path = os.path.join(
            os.path.join(os.getenv("ANALITICO_DRIVE", ""), "models", blessed_model_id, "metadata.json")
        )
        try:
            blessed_metrics = read_json(blessed_metadata_path)
            blessed_metrics = blessed_metrics.get("scores")
        except Exception as exc:
            logging.warning("metrics for the blessed model %s cannot be retrieved: \n%s", blessed_model_id, exc)

    current_metrics = {}
    try:
        current_metrics = read_json(os.path.join(os.path.dirname(notebook_path), "metadata.json"))
    except Exception as exc:
        logging.warning("metrics for the current execution cannot be retrieved: \n%s", exc)

    source_path = "/app/tasks/bless.py"
    bless_args = {
        "current_metrics": current_metrics,
        "blessed_model_id": blessed_model_id,
        "blessed_metrics": blessed_metrics,
    }
    cell = nbformat.v4.new_code_cell(
        source=read_text(source_path).format(**bless_args), metadata={"name": "analitico_bless_cell"}
    )
    notebook_node.cells.append(cell)

    return notebook_node


def remove_bless_cell(notebook_node):
    """ Remove the Analitico cell with the invocation of the bless() method. """
    notebook_node.cells = [
        cell for cell in notebook_node.cells if "analitico_bless_cell" != cell.metadata.get("name", "")
    ]
    return notebook_node


try:

    # enable logging by default
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Running...")

    # support the the pip installation of requirements with requirements.txt
    requirements_name = os.path.join(os.environ.get("ANALITICO_ITEM_PATH"), "requirements.txt")
    if os.path.exists(requirements_name):
        subprocess_run(["pip", "install", "-r", "requirements.txt"])

    # retrieve notebook that should be executed
    notebook_path = os.path.expandvars(args.notebooks[0])
    assert os.path.exists(notebook_path), f"Notebook {notebook_path} could not be found."
    notebook_dir = os.path.dirname(notebook_path)
    notebook = read_json(notebook_path)

    logging.info("Cleaning notebook from error cells of previous execution")
    notebook = nb_clear_error_cells(notebook)
    save_json(notebook, notebook_path)

    # process commands embedded in our notebook first to install dependencies, etc
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            # make sure lines contains individual lines, notebooks sometimes
            # have a single string of multiple lines and sometimes have an array of lines
            lines = cell["source"]
            if isinstance(lines, list):
                lines = "".join(lines)
                lines = lines.splitlines()

            for j, line in enumerate(lines):
                # extract ! lines for scripts, no % magic lines
                if line and line[0] == "!":
                    # command that should be passed to setup script
                    cmd = line[1:]
                    logging.info(f"# cell: {i+1}, line: {j+1}\n{cmd}\n\n")
                    try:
                        # run the cmd in the workdir of the notebook
                        # and directly to the shell without parsing the arguments
                        subprocess_run(cmd, shell=True, cwd=notebook_dir)
                    except Exception as exc:
                        raise AnaliticoException(
                            f"Error while preprocessing {notebook_path}, command: {cmd}, exc: {exc}"
                        ) from exc

    # process notebook with papermill
    try:
        os.chdir(notebook_dir)
        logging.info("Notebook: " + notebook_path)
        logging.info("Notebook directory: " + os.getcwd())
        logging.info("Running papermill to process notebook")

        # alter the notebook by adding the bless invocation
        # of the bless() function
        notebook_node = load_notebook_node(notebook_path)
        notebook_node = add_bless_cell(notebook_node)

        # work on a temporary file to not alter the original notebook
        with tempfile.NamedTemporaryFile(suffix=".ipynb") as f:
            write_ipynb(notebook_node, f.name)
            notebook_node = papermill.execute_notebook(f.name, f.name, cwd=notebook_dir, log_output=True)

        notebook_node = remove_bless_cell(notebook_node)
        write_ipynb(notebook_node, notebook_path)

    except Exception as exc:
        raise AnaliticoException(f"Error while processing {notebook_path}, exc: {exc}") from exc

except Exception:
    # when job does `run and build` error notification must be sent
    notification_url = os.environ.get("ANALITICO_NOTIFICATION_URL")
    if os.environ.get("ANALITICO_JOB_ACTION") == ACTION_RUN_AND_BUILD and notification_url:
        try_request_notification(notification_url)
    raise
finally:
    # eclude when job does `run and build` to let the build send the notification
    notification_url = os.environ.get("ANALITICO_NOTIFICATION_URL")
    if os.environ.get("ANALITICO_JOB_ACTION") == ACTION_RUN and notification_url:
        try_request_notification(notification_url)

logging.info("Done")
exit(code=0)
