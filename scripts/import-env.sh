#!/bin/bash
set -e
echo "Injecting env"
BASEDIR=$(dirname "$0")
source $BASEDIR/../../analitico-ci/analitico-env.sh

export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8

MYHOME="/home/www"
# if home does not exists use user home folder
if [ ! -d "/home/www" ] 
then
    MYHOME=~
fi
echo $MYHOME
export HOME=$MYHOME
export PYTHONPATH=$MYHOME/analitico/source/
# Path to admin.conf for kubectl
export KUBECONFIG="/home/www/analitico-ci/k8/admin.conf"

echo "Activate virtual env"

source $BASEDIR/../venv/bin/activate