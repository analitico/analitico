# Baseline is anaconda
FROM continuumio/anaconda3

# Run as root
USER root

RUN apt-get install -y nano less

# Install nginx and remove configuration
RUN  apt-get install -y gcc nginx curl apt-transport-https ca-certificates software-properties-common && rm /etc/nginx/nginx.conf 

# Install node and yarn for web app
RUN /bin/bash -c 'curl -sL https://deb.nodesource.com/setup_10.x | bash && apt-get install -y nodejs && curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list && apt-get update && apt-get install yarn'

# Install Google Cloud SDK (this is used by workers and unit tests)
RUN /bin/bash -c 'echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && apt-get update && apt-get install -y google-cloud-sdk'

# Install Docker Cli (this is used by workers and unit tests )
RUN /bin/bash -c 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable" && apt-get update && apt-get install -y docker-ce-cli'

# Install KubeControl for k8 Api Server communication
RUN /bin/bash -c 'curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list && apt-get update && apt-get install -y kubectl'

# create www user and add privileges as root in docker
RUN adduser www --disabled-login --disabled-password  --gecos "" && adduser www root

# copy codebase repo
COPY ./analitico /home/www/analitico

# copy secrets
COPY ./analitico-ci /home/www/analitico-ci

WORKDIR /home/www/analitico

# create python venv
RUN /bin/bash -c 'python3 -m venv venv'

# build everything
RUN /bin/bash -c './scripts/build.sh'