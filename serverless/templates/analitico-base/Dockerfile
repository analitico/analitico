FROM continuumio/anaconda3:2019.07

# Current production version of Kubernetes
ARG KUBECTL_PACKAGE_VERSION=1.14.2-00

ENV LANG=C.UTF-8
ENV LC_CTYPE=C.UTF-8

# Since anaconda3:2019.07 the path is not set
# when RUN is executed and so pip is not found
ENV PATH=$PATH:/opt/conda/bin/

# Script for running the Docker deamon
COPY dockerd-entrypoint.sh /usr/local/bin/

# Utils packages
RUN apt-get update
RUN apt-get install -y nano less curl procps apt-transport-https ca-certificates software-properties-common gnupg2
RUN apt-get install -y curl apt-transport-https ca-certificates software-properties-common gnupg2
# Missing in Anaconda3, required by docker python package
RUN apt-get install -y python3-distutils
# Should not be useful anymore after this ticket
# server / clean up and update requirements #143
# Required because we are not using conda virtual env
ENV PYTHONPATH=$PYTHONPATH:/opt/conda/lib/python3.7/site-packages
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Install Google Cloud SDK (for storage and Docker registry)
RUN /bin/bash -c 'echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && apt-get update && apt-get install -y google-cloud-sdk'

# Install Docker Cli and deamon (for builder job)
RUN /bin/bash -c 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable" && apt-get update && apt-get install -y docker-ce-cli docker-ce'

# Install KubeControl at the given version for k8 Api Server communication
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list && apt-get update
RUN apt-get install -y kubectl=$KUBECTL_PACKAGE_VERSION

# Create www user and add privileges as root in docker
RUN adduser www --disabled-login --disabled-password  --gecos "" && adduser www root

ENV HOME=/home/www
WORKDIR /home/www/analitico