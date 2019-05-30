
## knative baseline docker
### eu.gcr.io/analitico-api/knative-baseline

This is the baseline image used when building the knative image used to turn Jupyter
notebooks into runnable, standalone containers. The purpose of the baseline image
is to install the main dependencies so that when we build the actual images we end up
with a quicker build and smaller binaries.

This image needs to be rebuild every once in a while so that it can download the latest
versions of libraries in requirements.txt

To build the baseline image cd into this directory then:  
`docker build -t eu.gcr.io/analitico-api/knative-baseline .`

To push the newly built image to the private repository:  
`docker push eu.gcr.io/analitico-api/knative-baseline`
