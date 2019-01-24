FROM registry.gitlab.com/analitico/analitico
COPY . /home
WORKDIR /home/analitico
RUN pip3 install -r requirements.txt