FROM registry.gitlab.com/analitico/analitico
WORKDIR /home
ADD . ./
WORKDIR /home/analitico
RUN python3 -m pip install -r requirements.txt