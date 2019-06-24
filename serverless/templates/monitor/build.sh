#!/bin/bash

# directory that is hosting this file
PARENT_PATH=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

# copy requirements
cp $PARENT_PATH"/../../../../analitico-ci/monitor/config.json" .

# build image
docker build -t eu.gcr.io/analitico-api/analitico-monitor .

rm config.json