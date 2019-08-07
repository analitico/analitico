#!/bin/bash

# Starts the django builder command which is used in a kubernets job
# to build recipe contents into a docker image that can be used for serverless
# deployments. The information on the built image is saved in a model.

# TODO analitico-baseline image should be build with environment vars set #292

if ! pgrep dockerd
then
    echo "Running docker daemon..."
    # run and wait it starts listening
    dockerd-entrypoint.sh &> /dev/null &
    sleep 5s
fi

BASEDIR=$(dirname "$0")
source $BASEDIR/import-env.sh
cd $BASEDIR/../source

echo "Starting builder..."
# eg: ./manage.py builder rx_9u8x8xom ml_b5l4ffj4 my-notebook.ipynb
./manage.py builder $1 $2 $3

exit 0