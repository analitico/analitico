#!/bin/bash
# exit if error
set -e
# Build and test execution
echo "Injecting env"
source analitico-env
cd /home/www/analitico

echo "Start gunicorn"
mkdir -p /var/log/gunicorn/
exec /home/www/analitico/conf/gunicorn_start.sh &

echo "Start nginx"
nginx
echo "Wait"
wait
wait
echo "Done"