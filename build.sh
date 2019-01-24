#!/bin/bash

# Build and test execution

echo "Building"

# Load injected env
source analitico-env
source venv/bin/activate
pip3 install -r requirements.txt
cd source
echo "Static"
./manage.py collectstatic --noinput
#./manage.py test