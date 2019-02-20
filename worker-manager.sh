#!/bin/bash
# Keep a fixed number of worker dockers running
set -e

$TOTAL_WORKERS = 4
$DOCKER_PATH = $(</home/www/analitico/docker-path.txt)
# goes forever
while true
do
    # remove all worker dockers that have terminated
    docker rm -v -f $(docker ps -a -q -f status=exited -f name=analitico-worker)
    # count number of running workers
    $running_workers = $(docker ps -a -q -f status=running -f name=analitico-worker | wc -l)
    # calculate how many workers are missing according to the target
    $new_workers_needed = $TOTAL_WORKERS - $running_workers
    echo 'Running workers: ' $running_workers ', new workers needed: ' $new_workers_needed
    # start new worker dockers
    for ((i=0; i<$new_workers_needed; i++))
    do
        # generate random name for docker
        $docker_name = 'analitico-worker-'$(date +"%s")'-'$((1 + RANDOM % 1000000))
        # start docker with worker process
        docker run --name=$docker_name $DOCKER_PATH ./worker.sh
    done
    # wait a bit before checking again
    echo 'New workers started'
    sleep 30
done