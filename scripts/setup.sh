#!/bin/bash
# Sets up virtual environment

echo "Checking virtual environment..."
cd ~/analitico/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
