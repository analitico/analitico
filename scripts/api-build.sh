#!/bin/bash
# exit if error
set -e

echo "Injecting secrets"
source /home/www/analitico-ci/analitico-env.sh

echo "$(date +'%T'): Build analitico api and test"

cd /home/www/analitico

echo "Installing requirements"
pip install pip==20.1.1
pip install -r requirements.txt
# since python 3.6 the `enum34` is no longer compatible with the standard library.
# it should be fixed with the ticket `server / clean up and update requirements #143`
# `typing` library raises exception when collecting Django statics:
# `AttributeError: type object 'Callable' has no attribute '_abc_registry'`
PYTHONPATH="" pip uninstall -y enum34 typing

echo "Collect static"
cd source
python3 ./manage.py collectstatic --noinput

echo "Run tests"
# do not use docker for papermill unit tests (it is not supported on Gitlab CI)
python3 ./manage.py test --exclude-tag=slow --exclude-tag=docker

echo "Done"