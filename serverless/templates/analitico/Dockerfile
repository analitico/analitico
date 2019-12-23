# Starts from an image with default analitico packages
FROM eu.gcr.io/analitico-api/analitico-base:56ac2be65a24f93194a2d3bf47ba7bb4f9bbaaf6

ENV HOME=/home/www

# Analitico Source
COPY ./analitico /home/www/analitico
# Analitico Secrets
COPY ./analitico-ci /home/www/analitico-ci

# Configure Google Cloud SDK
RUN /bin/bash -c 'gcloud auth activate-service-account --key-file /home/www/analitico-ci/gcloud/analitico-api-service-account-key.json; \
    gcloud config set project analitico-api; \
    gcloud config set run/region us-central1; \
    gcloud -q auth configure-docker;'

# Configure Kubernetes Kubectl
ENV KUBECONFIG=/home/www/analitico-ci/k8/admin.conf

# Setup analitico and test
ENV PYTHONPATH=$PYTHONPATH:/home/www/analitico/source
RUN /bin/bash -c '$HOME/analitico/scripts/api-build.sh'

# Fix permissions on temp folder.
# build / analitico / run tests as gunicorn user (www) #398 
RUN chmod -R 777 /tmp

# Cleanup
RUN rm -Rf $HOME/.google*
