#!/bin/bash
# Build static Python assets and execute Python tests
# exit if error
set -e

cd /home/www/analitico/
echo "Injecting env"
source /home/www/analitico-ci/analitico-env.sh
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8
export HOME="/home/www"

echo "Installing requirements"
source venv/bin/activate
pip3 install -r requirements.txt

cd source

echo "Build Static"
./manage.py collectstatic --noinput

# make tmp and subfolders public
chmod -R 777 /tmp

echo "Running python tests"
./manage.py test

# make tmp and subfolders public
chmod -R 777 /tmp
