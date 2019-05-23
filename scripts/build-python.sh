#!/bin/sh
# Build static Python assets and execute Python tests
# exit if error
set -e

cd /home/www/analitico/
echo "Injecting env"
source /home/www/analitico-ci/analitico-env.sh
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8
export HOME="/home/www"
# unit tests require access to analitico package (import analitico)
export PYTHONPATH=/home/www/analitico/source

echo "Installing requirements"
source venv/bin/activate
pip3 install -r requirements.txt

cd source

echo "Build Static"
./manage.py collectstatic --noinput

# do not use docker for papermill unit tests (it is not supported on Gitlab CI)
unset ANALITICO_PAPERMILL_DOCKER_SCRIPT

echo "Configuring GCloud"
gcloud auth activate-service-account --key-file /home/www/analitico-ci/gcloud/analitico-api-service-account-key.json
gcloud config set project analitico-api
gcloud config set run/region us-central1

echo "Running python tests"
./manage.py test

# make tmp and subfolders public
chmod -R 777 /tmp
