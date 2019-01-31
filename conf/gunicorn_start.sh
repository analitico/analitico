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

# Start your Django Unicorn. The script is started directly from inside the
# virtual environment which will activate the environment itself.
# Programs meant to be run under supervisor should not daemonize themselves 
# (do not use --daemon)
exec /home/www/analitico/venv/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user $USER \
  --bind=unix:$SOCKFILE \
  --access-logfile /var/log/gunicorn/access.log \
  --access-logformat '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %({Content-Length}i)s %(L)s %(L)s "%(f)s" "%(a)s"'

# netdata is used to monitor the access log and report all sorts of information
# the access log needs to be written in a format that can be understood by netdata.
# we use the same format in ngix and in gunicorn, see examples below:

# nginx log format:
# '$remote_addr - $remote_user [$time_local] '
# '"$request" $status $body_bytes_sent '
# '$request_length $request_time $upstream_response_time '
# '"$http_referer" "$http_user_agent"';
#
# nginx example:
# 127.0.0.1 - - [27/Nov/2018:17:11:21 +0100] "POST /api/s24/order-sorting?format=json HTTP/1.1" 500 127 1465 0.005 0.004 "-" "PostmanRuntime/7.4.0"

# gunicorn example:
# 127.0.0.1 - - [27/Nov/2018:17:11:21 +0100] "POST /api/s24/order-sorting?format=json HTTP/1.0" 500 127 1101 0.004956 0.004956 "-" "PostmanRuntime/7.4.0"
# gunicorn documentation:
# http://docs.gunicorn.org/en/stable/settings.html#accesslog

