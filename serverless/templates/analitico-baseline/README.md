
## analitico-baseline
### eu.gcr.io/analitico-api/analitico-baseline

This is the image used to build analitico images (website, workers, etc...).
Rebuild when requirements are updated.

To build the baseline image cd into this directory then:  
`./build.sh`

To push the newly built image to the private repository:  
`docker push eu.gcr.io/analitico-api/analitico-baseline:base`

To get a token for accessing gcloud registry
`gcloud auth print-access-token`

Login gcloud registry
`docker login -u oauth2accesstoken eu.gcr.io/analitico-api/analitico-baseline:base`