#!/bin/bash

# use a different folder to avoid conflict 
# with analitico local files
mkdir -p jupyter
cd jupyter

if [[ -z "${ANALITICO_JUPYTER_TOKEN}" ]]; then
    echo "Jupyter token is not set" && exit 1
fi

# start jupyter server
echo "Start Jupyter notebook"
jupyter notebook \
    --port=$PORT \
    --ip=* \
    --allow-root \
    --no-browser \
    --notebook-dir="${ANALITICO_DRIVE}"  \
    --NotebookApp.allow_origin='*' \
    --NotebookApp.disable_check_xsrf=True \
    --NotebookApp.allow_password_change=False \
    --NotebookApp.token="${ANALITICO_JUPYTER_TOKEN}" \
    --ResourceUseDisplay.mem_warning_threshold=0.1 \
    --ResourceUseDisplay.mem_limit=${JUPYTER_MEM_LIMIT_BYTES}