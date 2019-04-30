#!/bin/bash
# exit if error
set -e
# import env
exec /home/www/analitico/scripts/import-env.sh

cd /home/www/analitico

echo "Start gunicorn"
mkdir -p /var/log/gunicorn/

NAME="website"                            # Name of the application
DJANGODIR=/home/www/analitico/source      # Django project directory
SOCKFILE=/tmp/gunicorn.sock               # we will communicate using this unix socket
USER=www                                  # the user to run as
GROUP=www                                 # the group to run as
NUM_WORKERS=8                             # how many worker processes should Gunicorn spawn
DJANGO_SETTINGS_MODULE=website.settings   # which settings file should Django use
DJANGO_WSGI_MODULE=website.wsgi           # WSGI module name

# Activate the virtual environment
cd $DJANGODIR

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE


# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# Start your Django Unicorn. The script is started directly from inside the
# virtual environment which will activate the environment itself.
# Programs meant to be run under supervisor should not daemonize themselves 
# (do not use --daemon)
exec /home/www/analitico/venv/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --timeout 900 \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user $USER \
  --bind=unix:$SOCKFILE \
  --access-logfile /var/log/gunicorn/access.log \
  --error-logfile  /var/log/gunicorn/error.log \
  --access-logformat '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %({Content-Length}i)s %(L)s %(L)s "%(f)s" "%(a)s"' &

echo "Start nginx"
nginx
echo "Wait"
wait
wait
echo "Done"