#!/bin/bash
# exit if error
set -e
# Build and test execution
cd /home/www/analitico/
echo "Injecting env"
source analitico-env
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8

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

# build static python and test
./build-python.sh
# build documentation
./build-docs.sh
# test angular app
./test-app.sh
# build angular app for production
./build-app.sh

echo "Done"