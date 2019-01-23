FROM ubuntu:18.04

RUN apk update && \
    apk add --no-cache vim bash

RUN apt-get install -y sudo
RUN apt install python-pip -y
RUN apt install python3.6-dev -y 
RUN apt install python3-venv -y  
RUN apt install build-essential
RUN apt install python3-dev -y 
RUN apt install nginx

RUN rm /etc/nginx.conf