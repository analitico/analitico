#!/bin/bash

NAME="website"                            # Name of the application
DJANGODIR=/home/www/analitico/source      # Django project directory
SOCKFILE=/tmp/gunicorn.sock               # we will communicate using this unix socket
USER=www                                  # the user to run as
GROUP=www                                 # the group to run as
NUM_WORKERS=1                             # how many worker processes should Gunicorn spawn
DJANGO_SETTINGS_MODULE=website.settings   # which settings file should Django use
DJANGO_WSGI_MODULE=website.wsgi           # WSGI module name

# Activate the virtual environment
echo "Starting $NAME as `whoami`"
cd $DJANGODIR

source /home/www/analitico/venv/bin/activate
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# Start your Django Unicorn. The script it started directly from inside the
# virtual environment which will activate the environment itself.
# Programs meant to be run under supervisor should not daemonize themselves 
# (do not use --daemon)
exec /home/www/analitico/venv/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user $USER \
  --bind=unix:$SOCKFILE

