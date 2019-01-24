FROM registry.gitlab.com/analitico/analitico:base
COPY . /home/analitico
WORKDIR /home/analitico
RUN /bin/bash -c "./build.sh"