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
export PYTHONPATH=$PYTHONPATH:$MYHOME/analitico/source/