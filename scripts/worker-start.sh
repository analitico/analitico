#!/bin/bash

# start a python worker process

BASEDIR=$(dirname "$0")

source $BASEDIR/import-env.sh

cd $BASEDIR/../source

echo "Starting worker..."
while true
do
    ./manage.py worker --max-secs 600 "$@" || true
    wait
    sleep 2
done
