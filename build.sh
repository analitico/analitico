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

echo "Running python tests"
./manage.py test

echo "Install angular modules"
cd /home/www/analitico/app
npm install

echo "Execute Angular tests"
#ng test

echo "Build Angular app"
ng build --outputHashing=all

echo "Link nginx conf"
sudo ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/nginx.conf

# TODO: copy SSL certificates
mkdir -p /home/www/ssl
echo "$ANALITICO_SSL_CRT" | base64 -d -w0 | tr -d '\r' > /home/www/ssl/analitico.ai.crt
echo "$ANALITICO_SSL_KEY" | base64 -d -w0 | tr -d '\r' > /home/www/ssl/analitico.ai.key
chmod 600 /home/www/ssl/analitico.ai.key
chmod 755 /home/www/ssl/analitico.ai.crt

# make tmp and subfolders public
chmod -R 777 /tmp

echo "Done"