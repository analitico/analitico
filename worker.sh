#!/bin/bash
# exit if error
set -e

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
