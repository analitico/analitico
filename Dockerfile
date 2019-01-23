FROM registry.gitlab.com/analitico/analitico

RUN cd /builds/analitico/analitico
RUN python3 -m venv venv
RUN source venv/bin/activate
RUN pip3 install -r requirements.txt