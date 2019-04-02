#!/bin/bash
# run jupyter notebooks in dockers
export LC_CTYPE=C.UTF-8

mkdir -p /home/www/notebooks
cd /home/www/analitico
source venv/bin/activate

jupyter notebook --port=$1 --ip=0.0.0.0 --no-browser \
--keyfile='/home/www/analitico-ci/ssl/analitico.ai.key' \
--certfile='/home/www/analitico-ci/ssl/analitico.ai.crt' \
--notebook-dir='/home/www/notebooks'  \
--NotebookApp.allow_origin='*' \
--NotebookApp.token="$2"
--NotebookApp.disable_check_xsrf=True &

wait
