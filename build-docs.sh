#!/bin/bash
# Build static documentation
# exit if error
set -e
# importing env
source /home/www/analitico/analitico-env
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8

cd /home/www/analitico/
echo "Installing requirements"
source venv/bin/activate
pip3 install -r requirements.txt

cd /home/www/analitico/documentation
# build docs
mkdocs build