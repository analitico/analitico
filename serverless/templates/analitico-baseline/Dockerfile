# Use the official Ubuntu image.
FROM ubuntu
# update packages
RUN  apt-get update &&  apt-get upgrade -y
RUN ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime && export DEBIAN_FRONTEND=noninteractive && apt-get install -y tzdata
# install python and deps
RUN apt-get install -y python-pip python3.6-dev python3-venv build-essential python3-dev python3-pip python3-tk nano less
# copy requirements
COPY ./requirements.txt ./requirements.txt
# create www user
RUN adduser www --disabled-login --disabled-password  --gecos ""
# switch to user www
USER www
# create analitico folder, create python venv, install requirements
RUN /bin/bash -c 'mkdir -p /home/www/analitico && cd /home/www/analitico && python3 -m venv venv && source venv/bin/activate && pip3 install wheel && pip3 install -r /requirements.txt'