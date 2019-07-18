#!/bin/bash
# exit if error
set -e
BASEDIR=$(dirname "$0")
# Build and test execution
cd /home/www/analitico/

echo "Injecting env"
source /home/www/analitico-ci/analitico-env.sh
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8


echo "Link nginx conf"
ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/nginx.conf

echo "$(date +'%T'): Build static python and test"

$BASEDIR/build-python.sh

echo "$(date +'%T'): Build docs"
# build documentation
$BASEDIR/build-docs.sh
echo "$(date +'%T'): Build app"
/home/www/analitico/app/build-app.sh

echo "Done"