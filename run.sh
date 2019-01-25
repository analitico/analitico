#!/bin/bash
# exit if error
set -e
# Build and test execution
echo "Injecting env"
source analitico-env
cd /home/www/analitico
source venv/bin/activate
echo "Start nginx"
exec nginx

echo "Start gunicorn"
cd source
exec gunicorn website.wsgi -b unix:/tmp/gunicorn.sock

echo "Done"