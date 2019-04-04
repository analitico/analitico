#!/bin/bash
# run jupyter notebooks in dockers
export LC_CTYPE=C.UTF-8
cd /home/www/analitico/
source venv/bin/activate
# genereate ssl keys
openssl req -x509 -nodes -days 7300 -newkey rsa:2048 -keyout key.pem -out cert.pem -subj "/C=US/O=Analitico/CN=analitico.ai"
# start jupyter notebook
jupyter notebook --port=$1 --ip=0.0.0.0 --no-browser \
--keyfile='/home/www/analitico/key.pem' \
--certfile='/home/www/analitico/cert.pem' \
--notebook-dir='/home/www/analitico/notebooks'  \
--NotebookApp.allow_origin='*' \
--NotebookApp.token="$2"
--NotebookApp.disable_check_xsrf=True &
# wait for temination
wait
