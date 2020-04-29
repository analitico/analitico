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
    --access-logformat '{ "method": "%(m)s", "path": "%(U)s", "query": "%(q)s", "status": %(s)s, "response_length": %(B)s, "content_length": %({content-length}i)s, "host": "%({host}i)s", "request_time": %(L)s, "user_agent": "%(a)s" }' \
    --log-level debug \
    --timeout 60 \
    app:app

# access log format documentation:
# https://docs.gunicorn.org/en/stable/settings.html#access-log-format

echo "Started"