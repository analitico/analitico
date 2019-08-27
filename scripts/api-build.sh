#!/bin/bash
# exit if error
set -e

echo "Injecting secrets"
source /home/www/analitico-ci/analitico-env.sh

echo "$(date +'%T'): Build analitico api and test"

cd /home/www/analitico

echo "Installing requirements"
pip install -r requirements.txt
# since python 3.6 the library is no longer compatible with the standard library
pip uninstall -y enum34

# unit tests require access to analitico package (import analitico)
export PYTHONPATH=$PYTHONPATH:/opt/conda/lib/python3.7/site-packages:/home/www/analitico/source

echo "Collect static"
cd source
python3 ./manage.py collectstatic --noinput

echo "Run tests"
# do not use docker for papermill unit tests (it is not supported on Gitlab CI)
unset ANALITICO_PAPERMILL_DOCKER_SCRIPT
python3 ./manage.py test --exclude-tag=slow --exclude-tag=docker

echo "Done"