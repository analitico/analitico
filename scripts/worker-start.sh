#!/bin/bash

# start a python worker process

# exit if error
set -e

exec /home/www/analitico/scripts/import-env.sh

cd /home/www/analitico/source

echo "Starting worker..."
./manage.py worker
