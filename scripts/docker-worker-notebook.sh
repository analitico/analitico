#!/bin/bash
# run jupyter notebooks in dockers
export LC_CTYPE=C.UTF-8
cd /home/www/analitico/
source venv/bin/activate
# Python libraries are in /libs
export PYTHONPATH=/home/www/analitico/libs/
# start jupyter notebook

# store arguments in a special array 
args=("$@") 
# get number of elements 
ELEMENTS=${#args[@]} 
parameters=""
for (( i=0;i<$ELEMENTS;i++)); do 
    parameters="${parameters} ${args[${i}]}"
done
echo $parameters
# execute papermill 
echo "Start papermill" 
papermill $parameters &

# wait for temination
wait
