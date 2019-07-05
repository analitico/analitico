#!/bin/bash

##
# Start a python worker process for executing live tests
##

BASEDIR=$(dirname "$0")

source $BASEDIR/import-env.sh

cd $BASEDIR/../source

echo "Starting worker..."
while true
do
    echo "Running tests..."

    # exec the command and intercept the error message
    # the `true` is required to let the loop continue on error
    { ERROR="$(./manage.py test --tag=live 2>&1 1>&3 3>&- )";  } 3>&1 || EXITSTATUS=$? || true
    
    # notify slack in case of errors
    if [[ $EXITSTATUS -ne 0 ]]; then
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
        
        curl --silent \
             -X POST \
             -H "Accept: application/json" \
             -H "Content-Type:application/json" \
             --data "${CONTENT}" ${ANALITICO_SLACK_INTERNAL_WEBHOOK}
    else 
        echo "Tests completed with success."
    fi
    
    # 5 min between tests
    echo "Next run in 5 minutes"
    wait
    sleep 300
done
