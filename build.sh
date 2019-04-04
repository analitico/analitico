#!/bin/bash
# exit if error
set -e
# Build and test execution
cd /home/www/analitico/
# move analitico-ci out of analitico
mv -f analitico-ci /home/www/

echo "Injecting env"
source /home/www/analitico-ci/analitico-env.sh
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8

echo "Link nginx conf"
sudo ln -s /home/www/analitico/conf/nginx.conf /etc/nginx/nginx.conf

echo "$(date +'%T'): Build static python and test"

./build-python.sh

echo "$(date +'%T'): Build docs"
# build documentation
./build-docs.sh
echo "$(date +'%T'): Build app"
/home/www/analitico/app/build-app.sh

echo "Done"