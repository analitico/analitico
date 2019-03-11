#!/bin/bash

# start a python worker process

# exit if error
set -e

<<<<<<< HEAD
echo "Injecting env"
source ~/analitico-ci/analitico-env.sh


echo "Checking virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "Starting worker..."
echo "Launching Jupyter..."
cd source
./manage.py worker

echo "Done"
=======
# Injecting env
source /home/www/analitico-ci/analitico-env.sh
cd /home/www/analitico
# start virtual env
source venv/bin/activate
# run worker
exec python3 source/manage.py worker
>>>>>>> 237f5e2f50eb539ee8d1b62bf83f9a30433b72da
