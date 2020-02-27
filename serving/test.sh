# create virtual environment if not there already
apt-get update
apt-get -y install python3-dev
python3 -m venv venv

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

export PYTHONPATH=../source
cd test
pytest *_test.py --html=reports/pytest-report.html --cov=analitico_etl

