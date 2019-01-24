FROM registry.gitlab.com/analitico/analitico
COPY . /home/analitico
WORKDIR /home/analitico
RUN pip3 install -r requirements.txt