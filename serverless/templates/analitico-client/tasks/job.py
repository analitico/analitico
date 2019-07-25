##
# Script executed for running a notebook by the job run
##

import logging
import os
import json
import argparse

# python libraries search path
os.environ["PYTHONPATH"] = os.path.expandvars("$PYTHONPATH:$ANALITICO_ITEM_PATH")

try:
    from analitico import AnaliticoException
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

# provide a basic command line interface to launch jobs
parser = argparse.ArgumentParser(description="Process a job.")
parser.add_argument(
    "notebooks", metavar="N", type=str, nargs="+", default="notebook.ipynb", help="a notebook file to be processed"
)
args = parser.parse_args()

# support the the pip installation of requirements with requirements.txt
requirements_name = os.path.join(os.environ.get("ANALITICO_ITEM_PATH"), "requirements.txt")
if os.path.exists(requirements_name):
    subprocess_run(["pip", "install", "-r", "requirements.txt"])


# retrieve notebook that should be executed
notebook_path = os.path.expandvars(args.notebooks[0])
assert os.path.exists(notebook_path), f"Notebook {notebook_path} could not be found."
notebook = read_json(notebook_path)

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
                cmd, cmd_args = line[1:], line[1:].split(" ")
                logging.info(f"# cell: {i+1}, line: {j+1}\n{cmd}\n\n")
                try:
                    subprocess_run(cmd_args)
                except Exception as exc:
                    raise AnaliticoException(
                        f"Error while preprocessing {notebook_path}, command: {cmd}, exc: {exc}"
                    ) from exc

# process notebook with papermill
try:
    notebook_dir = os.path.dirname(notebook_path)
    os.chdir(notebook_dir)
    logging.info("Notebook: " + notebook_path)
    logging.info("Notebook directory: " + os.getcwd())
    logging.info("Running papermill to process notebook")

    papermill.execute_notebook(notebook_path, notebook_path, cwd=notebook_dir)
except Exception as exc:
    raise AnaliticoException(f"Error while processing {notebook_path}, exc: {exc}") from exc

logging.info("Done")

exit(code=0)
