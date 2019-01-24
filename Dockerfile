FROM registry.gitlab.com/analitico/analitico
WORKDIR /home
ADD . ./
WORKDIR /home/analitico
RUN ls
RUN pip3 install -r requirements.txt