# analitico






## Environment

# Creating the virtual environment
python3 -m venv ~/envs/analitico

# Activate the environment
source python3 -m venv ~/envs/analitico

# Deactivate environment
deactivate

# See which packages are in use in the environment
pip freeze

# Update requirements file
pip freeze > requirements.txt

# Run with development server
python3 manage.py runserver

## Django Resources

Tutorial
https://docs.djangoproject.com/en/2.1/intro/tutorial01/
