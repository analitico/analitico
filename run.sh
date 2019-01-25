#!/bin/bash
# exit if error
set -e
# Build and test execution
echo "Injecting env"
source analitico-env

source venv/bin/activate
cd source

echo "Start nginx"
exec nginx

echo "Start gunicorn"
exec gunicorn website.wsgi -b unix:/tmp/gunicorn.sock

echo "Done"