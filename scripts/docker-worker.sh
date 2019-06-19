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
#echo $1
#echo $2
#echo $4
#echo $parameters

# create container name
DOCKERNAME='analitico-worker-'$(date +"%s")'-'$((1 + RANDOM % 1000000))
DOCKERIMAGENAME='image-'$DOCKERNAME
# use the jupyter image which is a safe env for untrusted code
# it is the same image that is used for "interactive mode" using Jupyter hosts
# it uses the same version (COMMIT_SHA) of the worker
docker run --name=$DOCKERNAME -d --init --runtime=nvidia eu.gcr.io/analitico-api/analitico-website:$ANALITICO_COMMIT_SHA-jupyter 
# copy working dir
docker cp $4/. $DOCKERNAME:/home/www/analitico/notebooks/
# copy script to execute notebook using papermill
docker cp $BASEDIR/docker-worker-notebook.sh $DOCKERNAME:/home/www/analitico/docker-worker-notebook.sh
# commit changes to the container as a image
docker commit $DOCKERNAME $DOCKERIMAGENAME
# remove current container
docker rm $DOCKERNAME
# run notebook in a new container using the prepared image
docker run --name=$DOCKERNAME -a stderr -a stdout --init --runtime=nvidia $DOCKERIMAGENAME /home/www/analitico/docker-worker-notebook.sh /home/www/analitico/notebooks/notebook.ipynb /home/www/analitico/notebooks/notebook.output.ipynb --cwd /home/www/analitico/notebooks/ $parameters
# wait papermill execution
EXITCODE=`docker wait $DOCKERNAME`

echo "Docker exit code $EXITCODE"
# copy working dir out of container
docker cp $DOCKERNAME:/home/www/analitico/notebooks/. $4
# remove container
docker rm $DOCKERNAME
# remove container image
docker image rm $DOCKERIMAGENAME
# return exit code of docker execution
exit $EXITCODE