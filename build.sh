#!/bin/bash
# exit if error
set -e
# Build and test execution
echo "Injecting env"
source analitico-env
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8

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
ng test

echo "Build Angular app"
ng build --prod --outputHashing=all

echo "Link nginx conf"
sudo ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/nginx.conf

# copy SSL certificates
mkdir -p /home/www/ssl
echo "$ANALITICO_SSL_CRT" | base64 -d -w0 | tr -d '\r' > /home/www/ssl/analitico.ai.crt
echo "$ANALITICO_SSL_KEY" | base64 -d -w0 | tr -d '\r' > /home/www/ssl/analitico.ai.key
chmod 600 /home/www/ssl/analitico.ai.key
chmod 755 /home/www/ssl/analitico.ai.crt

# copy CloudSQL certificates
mkdir -p /home/www/ssl/cloudsql
echo "$ANALITICO_MYSQL_SSL_CA" | base64 -d -w0 | tr -d '\r' > /home/www/ssl/cloudsql/client-ca.pem
echo "$ANALITICO_MYSQL_SSL_CERT" | base64 -d -w0 | tr -d '\r' > /home/www/ssl/cloudsql/client-cert.pem
echo "$ANALITICO_MYSQL_SSL_KEY" | base64 -d -w0 | tr -d '\r' > /home/www/ssl/cloudsql/client-key.pem
chmod 644 /home/www/ssl/cloudsql/*

# make tmp and subfolders public
chmod -R 777 /tmp

echo "Done"