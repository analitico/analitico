#!/bin/bash
# Copy ssl certificates from secret repo
# Build docker image

cp ../../../../analitico-ci/ssl/analitico.ai.crt .
cp ../../../../analitico-ci/ssl/analitico.ai.key .

if [[ "$1" == 'staging' ]]; then
    docker build --no-cache -t eu.gcr.io/analitico-api/k8-nginx-staging-balancer -f DockerfileStaging .
else
    docker build --no-cache -t eu.gcr.io/analitico-api/k8-nginx-balancer .
fi

rm analitico.ai.crt 
rm analitico.ai.key
