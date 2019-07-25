# analitico-base
### eu.gcr.io/analitico-api/analitico-base
This image only contains packages used by services.
It's built manually when we want to update Anaconda image or the version of the paclages.

To build the base image cd into this directory then: 

`./build.sh`

Then push the newly built image to the private repository: 

`docker push eu.gcr.io/analitico-api/analitico-base:latest`
