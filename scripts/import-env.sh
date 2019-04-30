#!/bin/bash
set -e
echo "Injecting env"
source /home/www/analitico-ci/analitico-env.sh

export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8
export HOME="/home/www"
export PYTHONPATH=/home/www/analitico/source

echo "Activate virtual env"
source /home/www/analitico/venv/bin/activate