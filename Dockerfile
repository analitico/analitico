FROM s6.analitico.ai:5000/analitico:base
COPY . /home/www/analitico
WORKDIR /home/www/analitico
RUN /bin/bash -c "./scripts/build.sh"