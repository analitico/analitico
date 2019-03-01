#!/bin/bash
# Test angular app
# exit if error
set -e

echo "Install angular modules"
cd /home/www/analitico/app
npm install

echo "Execute Angular tests"
#ng test
