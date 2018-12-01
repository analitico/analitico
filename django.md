
## Django Tutorials

Models fields, field types, foreign keys,     
https://docs.djangoproject.com/en/2.1/ref/models/fields/   

Authentication, authorization, permissions    
https://docs.djangoproject.com/en/2.1/topics/auth/default/   

Resetting migrations:
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc"  -delete
python manage.py makemigrations
python manage.py migrate

# sometimes if migrations fail it's because the api migration has not been created
python manage.py makemigrations api

# the 'api' migration needs to be applied first because it creates the user model
# which is then used by admin as a reference key in the django_admin_log table
# fake migration that fails because of custom user model
python manage.py migrate --fake admin 0001_initial