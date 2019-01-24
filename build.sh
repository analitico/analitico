#!/bin/bash

# Build and test execution
echo "Injecting env"
source analitico-env
echo "Installing requirements"
source venv/bin/activate
pip3 install -r requirements.txt

cd source

echo "Static"
./manage.py collectstatic --noinput

echo "Running tests"
./manage.py test

#sudo ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/
#nginx