#!/bin/bash
# Build static documentation
# exit if error
set -e
cd /home/www/analitico/documentation
# importing env
source /home/www/analitico/analitico-env
export LANG=C.UTF-8
export LC_CTYPE=C.UTF-8
# build docs
mkdocs build