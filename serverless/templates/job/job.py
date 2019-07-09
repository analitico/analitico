import logging
import os
import json
import argparse

from analitico import AnaliticoException
from analitico.utilities import read_json, subprocess_run

# enable logging by default
logging.getLogger().setLevel(logging.INFO)
logging.info("job.py running...")

# provide a basic command line interface to launch jobs
parser = argparse.ArgumentParser(description="Process a job.")
parser.add_argument(
    "notebooks", metavar="N", type=str, nargs="+", default="notebook.ipynb", help="a notebook file to be processed"
)
args = parser.parse_args()

# retrieve notebook that should be executed
notebook_path = args.notebooks[0]
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
    import papermill

    notebook_dir = os.path.dirname(notebook_path)
    papermill.execute_notebook(notebook_path, notebook_path, cwd=notebook_dir)
except Exception as exc:
    raise AnaliticoException(f"Error while processing {notebook_path}, exc: {exc}") from exc
