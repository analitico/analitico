FROM registry.gitlab.com/analitico/analitico
WORKDIR /home
RUN python3 -m venv venv
RUN source venv/bin/activate
RUN pip3 install -r requirements.txt