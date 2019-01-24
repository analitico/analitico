FROM registry.gitlab.com/analitico/analitico
COPY ./builds/analitico/analitico /home
WORKDIR /home/analitico
RUN pip3 install -r requirements.txt