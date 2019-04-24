#!/bin/bash
# run jupyter notebooks in dockers
export LC_CTYPE=C.UTF-8
cd /home/www/analitico/
source venv/bin/activate
export PYTHONPATH=/home/www/analitico/libs/
# start jupyter notebook
echo "Start jupyter notebook" 
exec jupyter notebook --port=8888 --ip=0.0.0.0 --no-browser \
--keyfile='/home/www/analitico/analitico.ai.key' \
--certfile='/home/www/analitico/analitico.ai.crt' \
--notebook-dir='/home/www/analitico/notebooks'  \
--NotebookApp.allow_origin='*' \
--NotebookApp.token="$1"
--NotebookApp.disable_check_xsrf=True &

# wait for temination
wait
