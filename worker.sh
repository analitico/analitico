#!/bin/bash

# start a python worker process

# exit if error
set -e

# Injecting env
source /home/www/analitico-ci/analitico-env.sh
cd /home/www/analitico
# start virtual env
source venv/bin/activate
# run worker
exec python3 source/manage.py worker