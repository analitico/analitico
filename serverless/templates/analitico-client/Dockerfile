FROM continuumio/anaconda3:2019.03

ENV WORKDIR /app
RUN mkdir /$WORKDIR

WORKDIR $WORKDIR

# Copy scripts to run a task
# Copy analitico SDK and s24 helper methods
# Copy analitico and user's requirements.txt files
# Copy commands collected from notebook (notebook.sh, if any) 
# Copy code extracted from the notebook (notebook.py)
COPY . .

RUN chmod +x ./tasks/serverless-start.sh

# Install analitico dependencies
RUN pip install -r analitico-requirements.txt

# Add libraries in base directory
ENV PYTHONPATH=$PYTHONPATH:$WORKDIR

##
# User's generated file
##

# User's dependencies
RUN pip install -r requirements.txt

# Setup commands collected from the notebook (if any)
RUN chmod +x notebook.sh
RUN ./notebook.sh
