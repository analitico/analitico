#!/bin/bash
# run jupyter notebooks in dockers
export LC_CTYPE=C.UTF-8
cd /home/www/analitico/
source venv/bin/activate

# start jupyter notebook
echo "Start jupyter notebook"
jupyter notebook --port=8888 --no-browser \
--notebook-dir='/home/www/analitico/notebooks'  \
--NotebookApp.allow_origin='*' \
--NotebookApp.token="$1"
--NotebookApp.disable_check_xsrf=True &

echo "Start nginx"
nginx
# wait for temination
wait
