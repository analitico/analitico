#!/bin/bash
# exit if error
set -e

# check if KNATIVE PORT is set and configure nginx
if [ -z "$PORT" ]
then
      echo "PORT is not set"
      exit 1
else
      echo "PORT is set to: $PORT"
fi


# import env
source /home/www/analitico/scripts/import-env.sh

cd /home/www/analitico

echo "Start gunicorn"
mkdir -p /var/log/gunicorn/

NAME="api"                                # Name of the application
DJANGODIR=/home/www/analitico/source      # Django project directory
USER=www                                  # the user to run as
GROUP=www                                 # the group to run as
NUM_WORKERS=9                             # (2*4CPU)+1, see: https://medium.com/building-the-system/gunicorn-3-means-of-concurrency-efbb547674b7
DJANGO_SETTINGS_MODULE=website.settings   # which settings file should Django use
DJANGO_WSGI_MODULE=website.wsgi           # WSGI module name

# Activate the virtual environment
cd $DJANGODIR

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE

# Start your Django Unicorn.
# Programs meant to be run under supervisor should not daemonize themselves 
# (do not use --daemon)
exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  --timeout 900 \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user $USER \
  --bind=:$PORT \
  --access-logfile /var/log/gunicorn/access.log \
  --error-logfile  /var/log/gunicorn/error.log \
  --access-logformat '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %({Content-Length}i)s %(L)s %(L)s "%(f)s" "%(a)s"' &

echo "Done"