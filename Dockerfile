FROM registry.gitlab.com/analitico/analitico
COPY . /home/analitico
WORKDIR /home/analitico
RUN /bin/bash -c "./build.sh"