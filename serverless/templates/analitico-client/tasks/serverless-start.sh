#!/bin/bash
# exit if error
set -e

# check if KNATIVE PORT is set and configure nginx
if [ -z "$PORT" ]
then
      echo "PORT variable is not set"
      exit 1
else
      echo "PORT variable is set to: $PORT"
fi

echo "Start gunicorn"

# Run the gunicorn webserver.
# Do not use threads because we don't know which libraries
# are run and thus they cant be not thread-safe. 
# Increase timeout to give more freedom to the user's endpoint.
# Custom access log format to add response time and X-forwarded-for host.
exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --access-logfile - \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %({content-length}i)s %(L)s "%(f)s" "%(a)s" "%({x-forwarded-for}i)s"' \
    --log-level debug \
    --timeout 60 \
    app:app

echo "Started"