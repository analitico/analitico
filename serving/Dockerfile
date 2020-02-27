# docker hub will build analitico:analitico-etl automatically from this repository
FROM python:3.7.6-buster

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Copy environment.yml (if found) to a temp locaition so we update the environment. Also
# copy "noop.txt" so the COPY instruction does not fail if no environment.yml exists.
COPY environment.yml* .devcontainer/noop.txt /tmp/conda-tmp/

# Copy etl source code and demo data
COPY source /root/source
COPY data /root/data
RUN chmod +x /root/source/analitico_serving/serving-start.sh

ENV PYTHONPATH "${PYTHONPATH}:/root/source"
ENV LANG "C.UTF-8"
ENV LC_CTYPE "C.UTF-8"

# Configure apt and install packages
RUN apt-get update \
    && apt-get -y install --no-install-recommends apt-utils dialog 2>&1 \
    #
    # Verify git, process tools, lsb-release (common in install instructions for CLIs) installed
    && apt-get -y install python3-dev git procps iproute2 lsb-release \
    #
    && python -V \
    && pip install --upgrade pip \
    && pip install pylint \
    && pip install pytest \
    && pip install psutil \
    && pip install black \
    && pip install mxnet \
    && pip install mxboard \
    && pip install bokeh \
    && pip install autogluon \
    && pip install requests==2.23.0 \
    && pip install gunicorn==20.0.4 \
    && pip install flask==1.1.1 \
    && pip install flask-cors==3.0.8 \
    && pip install simplejson==3.17.0 \
    #
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/source/analitico_serving

# Switch back to dialog for any ad-hoc use of apt-get
ENV DEBIAN_FRONTEND=
