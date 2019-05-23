FROM s6.analitico.ai:5000/analitico:base
COPY /home/www/analitico /home/www/analitico
COPY /home/www/analitico-ci /home/www/analitico-ci
WORKDIR /home/www/analitico