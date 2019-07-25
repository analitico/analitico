FROM continuumio/anaconda3:2019.03

# create www user and add privileges as root in docker
RUN adduser www --disabled-login --disabled-password  --gecos "" && adduser www root

ENV WORKDIR /home/www

WORKDIR $WORKDIR

# copy scripts to run a task
COPY ./tasks/app.py app.py
COPY ./tasks/job.py job.py

COPY ./tasks/prediction-start.sh prediction-start.sh
RUN chmod +x prediction-start.sh

# copy analitico SDK and s24 helper methods
# TODO /analitico and /s24 need to be built into standalone libraries
COPY ./analitico analitico
COPY ./s24 s24

# Install analitico dependencies
COPY ./analitico-requirements.txt analitico-requirements.txt
RUN pip install -r analitico-requirements.txt

# Add libraries in base directory
ENV PYTHONPATH=$PYTHONPATH:$WORKDIR

##
# User's generated file
##

# User's dependencies
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Setup commands collected from the notebook (if any)
COPY ./notebook.sh notebook.sh
RUN chmod +x notebook.sh
RUN ./notebook.sh

# Code extracted from the notebook
COPY ./notebook.py notebook.py
