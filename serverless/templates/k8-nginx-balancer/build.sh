#!/bin/bash
# Copy ssl certificates from secret repo
# Build docker image

cp ../../../../analitico-ci/ssl/analitico.ai.crt .
cp ../../../../analitico-ci/ssl/analitico.ai.key .

docker build -t eu.gcr.io/analitico-api/k8-nginx-balancer .

rm analitico.ai.crt 
rm analitico.ai.key
