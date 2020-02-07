FROM continuumio/anaconda3:2019.07

##
# Image setup
##

# since anaconda3:2019.07 the path is not set
# when RUN is executed and so pip is not found
ENV PATH=$PATH:/opt/conda/bin/

ENV LC_CTYPE=C.UTF-8
ENV WORKDIR /app
RUN mkdir /$WORKDIR

RUN apt-get update --fix-missing
# `psmisc` is used for `killall` command in Tensorboard script
# `python3-dev`, `gcc` and `g++` are used to compile Python packages
RUN apt-get install -y psmisc gcc g++ python3-dev

WORKDIR $WORKDIR

# Copy scripts to run a task
# Copy s24 helper methods
# Copy analitico and user's requirements.txt files
# Copy commands collected from notebook (notebook.sh, if any) 
# Copy code extracted from the notebook (notebook.py)
COPY . .

RUN chmod +x ./tasks/serverless-start.sh

# Install analitico dependencies
RUN pip install --upgrade pip
RUN pip install -r analitico-requirements.txt

# Add path to libraries
ENV PYTHONPATH=$PYTHONPATH:$WORKDIR/libraries

##
# Jupyter setup
##

RUN chmod +x ./tasks/jupyter-start.sh
RUN chmod +x ./tasks/tensorboard-start.py

# Generate configuration for Jupyter server
RUN mkdir -p jupyter
RUN /bin/bash -c "cd jupyter && jupyter notebook --generate-config"

##
# Serveless setup
##

# User's dependencies
RUN pip install -r requirements.txt

# Setup commands collected from the notebook (if any)
RUN chmod +x notebook.sh
RUN ./notebook.sh
