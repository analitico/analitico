#!/bin/bash

# Build and test execution
echo "Injecting env"
source analitico-env
echo "Installing requirements"
source venv/bin/activate
pip3 install -r requirements.txt

cd source

echo "Build Static"
./manage.py collectstatic --noinput

echo "Running tests"
./manage.py test

echo "Link nginx conf"
sudo ln -s /home/analitico/conf/nginx.conf /etc/nginx/

# TODO: copy SSL certificates

cd /home/www/analitico/source/
echo "Start gunicorn"
gunicorn website.wsgi -b unix:/tmp/gunicorn.sock

echo "Start nginx"
nginx

echo "Done"