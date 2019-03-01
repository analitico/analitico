FROM registry.gitlab.com/analitico/analitico:base
COPY . /home/www/analitico
COPY ../analitico-ci /home/www/analitico-ci
WORKDIR /home/www/analitico
RUN /bin/bash -c "./build.sh"