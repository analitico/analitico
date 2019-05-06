#!/bin/bash
# this is used by worker to run jupyter notebooks in dockers
# start jupyter notebook
set -x
# ANALITICO_COMMIT_SHA=f64473a6d09e5a5b94e1dfb2e0f5d6993f7364a0


BASEDIR=$(dirname "$0")
# store arguments in a special array 
args=("$@") 
# get number of elements 
ELEMENTS=${#args[@]} 

parameters=""
for (( i=4;i<$ELEMENTS;i++)); do 
    parameters="${parameters} ${args[${i}]}"
done
echo $1
echo $2
echo $4
echo $parameters

# create docker name
DOCKERNAME='analitico-worker-'$(date +"%s")'-'$((1 + RANDOM % 1000000))
DOCKERIMAGENAME='image-'$DOCKERNAME
docker run --name=$DOCKERNAME -d --init --runtime=nvidia registry.gitlab.com/analitico/analitico:$ANALITICO_COMMIT_SHA-jupyter 
# copy notebook
docker cp $4/. $DOCKERNAME:/home/www/analitico/notebooks/
# copy script
docker cp $BASEDIR/docker-worker-notebook.sh $DOCKERNAME:/home/www/analitico/docker-worker-notebook.sh
# commit status
docker commit $DOCKERNAME $DOCKERIMAGENAME
# remove current
docker rm $DOCKERNAME
# run notebook
docker run --name=$DOCKERNAME -d --init --runtime=nvidia $DOCKERIMAGENAME /home/www/analitico/docker-worker-notebook.sh /home/www/analitico/notebooks/notebook.ipynb /home/www/analitico/notebooks/notebook.output.ipynb --cwd /home/www/analitico/notebooks/ $parameters
docker wait $DOCKERNAME
docker cp $DOCKERNAME:/home/www/analitico/notebooks/. $4
docker rm $DOCKERNAME
docker image rm $DOCKERIMAGENAME