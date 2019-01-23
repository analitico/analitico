FROM registry.gitlab.com/analitico/analitico
COPY /builds/analitico/analitico /home
RUN cd /home/analitico
RUN python3 -m venv venv
RUN source venv/bin/activate
RUN pip3 install -r requirements.txt