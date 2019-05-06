#!/bin/bash

# start a python worker process

BASEDIR=$(dirname "$0")

source $BASEDIR/import-env.sh

cd $BASEDIR/../source
# overwrite papermill with docker script
alias papermill=/Users/gio/analitico/scripts/docker-worker.sh

echo "Starting worker..."
while true
do
    ./manage.py worker --max-secs 600 || true
    wait
    sleep 2
done
