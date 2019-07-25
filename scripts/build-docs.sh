#!/bin/bash
# Build static documentation
# exit if error
set -e

echo "Installing requirements"
pip install -r requirements.txt

# build s24 docs
pushd .
cd integrations/s24/documentation
mkdocs build --clean
popd

# build analitico docs
pushd .
cd documentation
mkdocs build --clean
ln -s ../../integrations/s24/documentation/site site/s24

popd
