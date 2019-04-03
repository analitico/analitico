#!/bin/bash
# run jupyter notebooks in dockers
export LC_CTYPE=C.UTF-8
cd ~
source venv/bin/activate

jupyter notebook --port=$1 --ip=0.0.0.0 --no-browser \
--keyfile='~/analitico.ai.key' \
--certfile='~/analitico.ai.crt' \
--notebook-dir='~/notebooks'  \
--NotebookApp.allow_origin='*' \
--NotebookApp.token="$2"
--NotebookApp.disable_check_xsrf=True &

wait
