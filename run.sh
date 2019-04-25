#!/bin/bash
# exit if error
set -e

echo "Injecting env"
source /home/www/analitico-ci/analitico-env.sh
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8
export HOME="/home/www"

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