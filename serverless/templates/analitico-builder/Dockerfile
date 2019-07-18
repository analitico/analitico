# docker image for docker in docker
FROM docker:stable-dind

COPY ./analitico /home/www/analitico
COPY ./analitico-ci /home/www/analitico-ci

RUN apk update && apk upgrade
RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime && export DEBIAN_FRONTEND=noninteractive && apk add tzdata

# install python and deps
# TODO use 3.7 non dev 
RUN apk add bash python3 py3-virtualenv

# create analitico folder, create python venv, install requirements
RUN /bin/bash -c 'cd /home/www/analitico && python3 -m venv venv && source venv/bin/activate && pip3 install wheel && pip3 install -r ./requirements.txt'
