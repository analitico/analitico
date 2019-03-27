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

# build static python and test
./build-python.sh
# build documentation
./build-docs.sh

/home/www/analitico/app/build-app.sh

echo "Done"