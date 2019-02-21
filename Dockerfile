FROM registry.gitlab.com/analitico/analitico:base
COPY . /home/www/analitico
WORKDIR /home/www/analitico
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
RUN /bin/bash -c "./build.sh"