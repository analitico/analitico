##
# Script executed for running a notebook by the job run
##

import logging
import os
import json
import argparse
import requests

import analitico.logging

# python libraries search path
os.environ["PYTHONPATH"] = os.path.expandvars("$PYTHONPATH:$ANALITICO_ITEM_PATH")

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


try:

    try:
        from analitico import AnaliticoException, ACTION_RUN, ACTION_RUN_AND_BUILD
        from analitico.utilities import read_json, subprocess_run
    except Exception as exc:
        raise AnaliticoException(f"Analitico dependencies should be installed.") from exc

    try:
        import papermill
    except Exception as exc:
        raise AnaliticoException(f"Papermill dependency should be installed.") from exc

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

    notebook = nb_clear_error_cells(notebook)
    
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

        papermill.execute_notebook(notebook_path, notebook_path, cwd=notebook_dir, log_output=True)
    except Exception as exc:
        raise AnaliticoException(f"Error while processing {notebook_path}, exc: {exc}") from exc
except Exception:
    # when job does `run and build` error notification must be sent
    notification_url = os.environ.get("ANALITICO_NOTIFICATION_URL")
    if os.environ.get("ANALITICO_JOB_ACTION") == ACTION_RUN_AND_BUILD and notification_url:
        try_request_notification(notification_url)
    raise
finally:
    # eclude when job does `run and build`
    notification_url = os.environ.get("ANALITICO_NOTIFICATION_URL")
    if os.environ.get("ANALITICO_JOB_ACTION") == ACTION_RUN and notification_url:
        try_request_notification(notification_url)

logging.info("Done")
exit(code=0)
