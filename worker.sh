#!/bin/bash
# exit if error
set -e

echo "Injecting env"
source /home/www/analitico-ci/analitico-env.sh
cd /home/www/analitico

echo "Start worker"

#exec /home/www/analitico/conf/gunicorn_start.sh &

echo "Done"