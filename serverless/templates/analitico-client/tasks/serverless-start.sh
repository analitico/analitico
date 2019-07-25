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

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --access-logfile - \
    --log-level debug \
    app:app

echo "Started"