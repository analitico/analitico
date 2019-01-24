FROM registry.gitlab.com/analitico/analitico
WORKDIR /home
ADD . ./
WORKDIR /home/analitico
RUN pip3 install -r requirements.txt