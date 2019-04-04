#!/bin/bash
# run jupyter notebooks in dockers
export LC_CTYPE=C.UTF-8
cd /home/www/analitico/
source venv/bin/activate

jupyter notebook --port=$1 --ip=0.0.0.0 --no-browser \
--keyfile='/home/www/analitico/analitico.ai.key' \
--certfile='/home/www/analitico/analitico.ai.crt' \
--notebook-dir='/home/www/analitico/notebooks'  \
--NotebookApp.allow_origin='*' \
--NotebookApp.token="$2"
--NotebookApp.disable_check_xsrf=True &

wait
