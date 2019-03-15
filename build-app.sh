#!/bin/bash
# Build angular app
# exit if error
set -e

echo "Install angular modules"
cd /home/www/analitico/app
npm install

echo "Build Angular app"
ng build --prod