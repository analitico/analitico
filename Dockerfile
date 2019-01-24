FROM registry.gitlab.com/analitico/analitico
WORKDIR /home
ADD . ./
WORKDIR /home/analitico
RUN python3 -m venv venv
RUN . venv/bin/activate
RUN pip3 install -r requirements.txt