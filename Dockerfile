FROM registry.gitlab.com/analitico/analitico:base
COPY . /home/www/analitico
WORKDIR /home/www/analitico
RUN /bin/bash su -c "./build.sh" www