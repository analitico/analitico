#!/bin/bash
# Runs Jupyter in its virtual environment. If you don't have
# echo a virtual env setup you should run ./jupyter-setup.sh first

echo "Checking virtual environment..."
cd ~/analitico/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# how do I add to jupyter path?
# export PATH=$PATH:~/github/analitico/source
# export JUPYTER_PATH=~/github/analitico/source:$JUPYTER_PATH

echo "Launching Jupyter..."
#cd notebooks
jupyter notebook