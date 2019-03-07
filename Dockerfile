FROM registry.gitlab.com/analitico/analitico:base
COPY . /home/www/analitico
WORKDIR /home/www/analitico
RUN whoami
USER www
RUN whoami
RUN /bin/bash -c "./build.sh"