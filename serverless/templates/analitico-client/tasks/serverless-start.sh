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

# (2*0.5CPU)+1, 
# see https://medium.com/building-the-system/gunicorn-3-means-of-concurrency-efbb547674b7
THREADS=2 

# Run the gunicorn webserver
exec gunicorn \
    --bind :$PORT \
    --threads $THREADS \  
    --access-logfile - \
    --log-level debug \
    app:app

echo "Started"