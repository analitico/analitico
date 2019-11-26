#!/bin/bash

##
# Execute Analitico tests tagged as `live`.
#
# First, is run the docker deamon used by tests that require to build images.
# This script is run on the `analitico` image that has already installed
# a docker deamon and the script to run the deamon.
##

if ! pgrep dockerd
then
    echo "Running docker daemon..."
    # run and wait it starts listening
    dockerd-entrypoint.sh &> /dev/null &
    sleep 5s
fi

BASEDIR=$(dirname "$0")
source $BASEDIR/import-env.sh
cd $BASEDIR/../source

# start a python worker process for executing

echo "Starting worker..."
while true
do
    echo "$(date -u) - Running tests..."
    STARTTIME="$(date -u +%s)"

    # exec the command and intercept the error message
    # the `true` is required to let the loop continue on error
    CMD_TEST="./manage.py test --tag=live"
    { ERROR="$($CMD_TEST 2>&1 1>&3 3>&- )";  } 3>&1 || EXITSTATUS=$? || true
    
    COMPLETEDTIME="$(date -u +%s)"
    RUNNING_TIME_MIN="$((($COMPLETEDTIME - STARTTIME) / 60))"

    # notify slack in case of errors
    if [[ $EXITSTATUS -ne 0 ]]
    then
        echo "Tests failed"

        # extract test results
        [[ $(echo $ERROR) =~ (\=== (.*?) \---) ]]

        echo ${BASH_REMATCH[0]}

        # escape double quotes
        ERROR=${BASH_REMATCH[0]//'"'/'\"'}

        CONTENT="$(printf '{"text": "%s", "attachments": [ {"text": "%s", "color": "%s" } ] }' \
                "Live tests failed" \
                "${ERROR}" \
                "danger")"
    else 
        CONTENT="$(printf '{"text": "%s", "attachments": [ {"text": "%s", "color": "%s" } ] }' \
                "Live tests completed" \
                "Live tests completed with success in ${RUNNING_TIME_MIN} minutes" \
                "good")"
    fi

    curl --silent \
             -X POST \
             -H "Accept: application/json" \
             -H "Content-Type:application/json" \
             --data "${CONTENT}" ${ANALITICO_SLACK_INTERNAL_WEBHOOK} || true
    
    echo "Run completd in ${RUNNING_TIME_MIN} minutes."

    # 5 min between tests
    echo "Next run in 60 minutes"
    
    sleep 3600
done
