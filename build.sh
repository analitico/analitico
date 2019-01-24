#!/bin/bash

# Build and test execution

echo "Building"

# Load injected env
source analitico-env
# requirements
pip3 install -r requirements.txt
# static
./source/manage.py collectstatic --noinput
# test
echo "Testing"
./source/manage.py test
