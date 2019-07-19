
## analitico
### eu.gcr.io/analitico-api/analitico

This is the image built by Gitlab CI that contains all the Analitico Env (secrets included!). 

### eu.gcr.io/analitico-api/analitico:base
To build the base image cd into this directory then: 

`./build.sh`

Then push the newly built image to the private repository: 

`docker push eu.gcr.io/analitico-api/analitico:base`

#### Note:
DockerfileJupyter is DEPRECATED and will be replaced by k8 jupyter services



