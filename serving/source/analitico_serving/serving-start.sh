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
# Timeout is required to load heavy models.
exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --access-logfile - \
    --log-level info \
    --timeout 600 \
    "app:create_app()"

echo "Started"