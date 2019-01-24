FROM registry.gitlab.com/analitico/analitico
WORKDIR /home
ADD . ./
WORKDIR /home/analitico
RUN /bin/bash -c 'python3 -m venv venv'
RUN /bin/bash -c 'source venv/bin/activate'
RUN /bin/bash -c 'pip3 install -r requirements.txt'