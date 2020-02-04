#!/bin/bash
# exit if error
set -e

echo "Injecting secrets"
source /home/www/analitico-ci/analitico-env.sh

echo "$(date +'%T'): Build analitico api and test"

cd /home/www/analitico

echo "Installing requirements"
pip install --upgrade pip
pip install -r requirements.txt
# since python 3.6 the library is no longer compatible with the standard library.
# it should be fixed with the ticket 
# server / clean up and update requirements #143
PYTHONPATH="" pip uninstall -y enum34

echo "Collect static"
cd source
./manage.py collectstatic --noinput

echo "Run tests"
# do not use docker for papermill unit tests (it is not supported on Gitlab CI)
./manage.py test --exclude-tag=slow --exclude-tag=docker

echo "Done"