#!/bin/bash

# directory that is hosting this file
PARENT_PATH=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

# copy requirements
cp $PARENT_PATH"/../../../requirements.txt" .

# build image
docker build -t eu.gcr.io/analitico-api/analitico-baseline:base .

# remove copy of requirements.txt
rm requirements.txt