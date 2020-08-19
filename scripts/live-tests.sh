#!/bin/bash

##
# Execute Analitico endpoints for monitoring
#
##


BASEDIR=$(dirname "$0")
source $BASEDIR/import-env.sh

# start a worker process for executing

# endpoints to monitor
declare -A names
declare -A endpoints
names[0]="API (without load balancer)"
endpoints[0]='curl --silent --show-error --fail -H "Host:api.cloud.analitico.ai" -X GET https://s1.analitico.ai:31390/api/runtime'

names[1]="api/jobs/schedule (cron)"
endpoints[1]='curl --silent --show-error --fail -H "Authorization:Bearer tok_tester1_Xf4dfG345B" -X GET https://analitico.ai/api/jobs/schedule'

names[2]="api/datasets"
endpoints[2]='curl --silent --show-error --fail -X GET https://analitico.ai/api/datasets?token=tok_tester1_Xf4dfG345B&test=true'

names[3]="app"
endpoints[3]='curl --silent --show-error --fail -X GET https://analitico.ai/app'

names[4]="elasticsearch (logs)"
endpoints[4]='curl --silent --show-error --fail -H "Authorization:Bearer tok_tester3_vgG42y6S" -X GET https://analitico.ai/api/recipes/rx_helloworld/k8s/services/production/logs?size=50'

names[5]="prometheus (metrics)"
endpoints[5]='curl --silent --show-error --fail -X GET https://prometheus.cloud.analitico.ai/-/healthy'


echo "Starting worker..."
while true
do
    echo "$(date -u) - Running tests..."
    STARTTIME="$(date -u +%s)"

    COMPLETEDTIME="$(date -u +%s)"
    RUNNING_TIME_SECS="$((($COMPLETEDTIME - STARTTIME)))"

    succeded=0
    failed=0

    len=${#endpoints[@]}
    for (( i=0; i<${len}; i++ ))
    do

        # exec the command and intercept the error message
        # the `true` is required to let the loop continue on error
        NAME_TEST=${names[$i]}
        CMD_TEST=${endpoints[$i]}
        EXITSTATUS=0

        OUTPUT=$(eval "$CMD_TEST" 2>&1) || EXITSTATUS=$? || true
        # escape double quotes
        OUTPUT=$(printf '%s' ${OUTPUT} | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')

        # notify slack in case of errors
        if [[ $EXITSTATUS -ne 0 ]]
        then
            echo "Tests failed"
            failed=$(($failed+1))

            CONTENT="$(printf '{"text": "%s", "attachments": [ {"text": %s, "color": "%s" } ] }' \
                    "Failed: ${NAME_TEST}" \
                    "${OUTPUT}" \
                    "danger")"

            curl --silent \
                -X POST \
                -H "Accept: application/json" \
                -H "Content-Type:application/json" \
                --data "${CONTENT}" ${ANALITICO_SLACK_INTERNAL_WEBHOOK} || true
        else
            succeded=$(($succeded+1))
        fi
    
    done
    # end loop

    # summary
    CONTENT="$(printf '{"text": "%s", "attachments": [ {"text": "%s", "color": "%s" } ] }' \
        "Monitor tests completed" \
        "Succeded: ${succeded} - Failed: ${failed} - Run: ${len}" \
        "good")"


    curl --silent \
        -X POST \
        -H "Accept: application/json" \
        -H "Content-Type:application/json" \
        --data "${CONTENT}" ${ANALITICO_SLACK_INTERNAL_WEBHOOK} || true

    echo ""
    echo "Run completd in ${RUNNING_TIME_SECS} minutes."

    # 5 min between tests
    echo "Next run in 60 seconds"
    
    sleep 60
done
