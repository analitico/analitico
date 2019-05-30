# Use the official Python image.
# https://hub.docker.com/_/python
FROM python:3.7

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . .

# Add libraries in base directory
ENV PYTHONPATH=$APP_HOME

# Install production dependencies.
RUN pip install Flask gunicorn
RUN pip install -r requirements.txt
