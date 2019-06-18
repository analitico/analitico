#!/bin/bash

# directory that is hosting this file
PARENT_PATH=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

# build image
docker build -t eu.gcr.io/analitico-api/analitico-website:base .
