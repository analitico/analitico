# Starts from an image with default analitico packages
FROM eu.gcr.io/analitico-api/analitico-base

ENV HOME=/home/www

# Analitico Source
COPY ./analitico /home/www/analitico
# Analitico Secrets
COPY ./analitico-ci /home/www/analitico-ci

# Fix permissions on temp folder
RUN chmod -R 777 /tmp

# Configure Google Cloud SDK
RUN /bin/bash -c 'gcloud auth activate-service-account --key-file /home/www/analitico-ci/gcloud/analitico-api-service-account-key.json; \
    gcloud config set project analitico-api; \
    gcloud config set run/region us-central1; \
    gcloud -q auth configure-docker;'

# Configure Kubernetes Kubectl
ENV KUBECONFIG=/home/www/analitico-ci/k8/admin.conf

# Setup analitico and test
RUN /bin/bash -c '$HOME/analitico/scripts/api-build.sh'

# Cleanup
RUN rm -Rf $HOME/.google*
