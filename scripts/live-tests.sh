#!/bin/bash

##
# Start a python worker process for executing live tests
##

BASEDIR=$(dirname "$0")

source $BASEDIR/import-env.sh

cd $BASEDIR/../source

echo "Starting worker..."
while true
do
    ./manage.py test --tag=live --tag=docker --tag=slow || true
    # non zero code -> stderr to slack
    # 5 min between tests
    wait
    sleep 300
done
