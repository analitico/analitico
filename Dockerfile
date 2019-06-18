FROM eu.gcr.io/analitico-api/analitico-website:base
COPY . /home/www/analitico
WORKDIR /home/www/analitico
RUN /bin/bash -c "./scripts/build.sh"