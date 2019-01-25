#!/bin/bash
# exit if error
set -e
# Build and test execution
echo "Injecting env"
source analitico-env

echo "Installing requirements"
source venv/bin/activate
pip3 install -r requirements.txt

cd source

echo "Build Static"
./manage.py collectstatic --noinput

#echo "Running tests"
#./manage.py test

echo "Link nginx conf"
sudo ln -s /home/www/analitico/conf/nginx-ci.conf /etc/nginx/nginx.conf

# TODO: copy SSL certificates

echo "Done"