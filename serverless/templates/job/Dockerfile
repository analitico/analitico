
# Anaconda contains pretty much any ML package we may need
FROM continuumio/anaconda3

# Copy local code to the container image
ENV APP_HOME /app
WORKDIR $APP_HOME

COPY job.py job.py
COPY requirements.txt requirements.txt

# Add libraries in base directory
ENV PYTHONPATH=$APP_HOME

# Install production dependencies
RUN pip install -r requirements.txt
