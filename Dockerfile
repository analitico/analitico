FROM registry.gitlab.com/analitico/analitico:base
COPY . /home/www/analitico
WORKDIR /home/www/analitico
USER www
RUN /bin/bash -c "./build.sh"