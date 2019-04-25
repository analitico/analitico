#!/bin/bash
# Runs Jupyter in its virtual environment. If you don't have
# echo a virtual env setup you should run ./jupyter-setup.sh first

echo "Checking virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "Launching Jupyter..."
jupyter notebook
