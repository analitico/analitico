#!/bin/bash

# Build and test execution

echo "Building"

# Load injected env
# source analitico-env
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
./manage.py collectstatic --noinput
#./manage.py test