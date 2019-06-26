# Use analitico's baseline image with base requirements.txt installed
FROM eu.gcr.io/analitico-api/knative-baseline

# Copy local code to the container image.
ENV APP_HOME /app

WORKDIR $APP_HOME
COPY . .

# Add libraries in base directory
ENV PYTHONPATH=$APP_HOME

# Install production dependencies.
RUN pip install Flask gunicorn
RUN pip install -r requirements.txt

# Run setup commands collected from the notebook (if any)
RUN chmod +x notebook.sh
RUN ./notebook.sh

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --access-logfile - app:app
