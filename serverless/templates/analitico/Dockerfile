# Starts from an image with default analitico packages
FROM eu.gcr.io/analitico-api/analitico:base

# copy codebase repo
COPY ./analitico /home/www/analitico

# copy secrets
COPY ./analitico-ci /home/www/analitico-ci

# create python venv
RUN /bin/bash -c 'python3 -m venv venv'

# build everything
RUN /bin/bash -c './scripts/build.sh'