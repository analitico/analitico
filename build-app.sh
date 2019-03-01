#!/bin/bash
# Build angular app
# exit if error
set -e

echo "Install angular modules"
cd /home/www/analitico/app
npm install --production

echo "Build Angular app"
ng build --prod --outputHashing=all
