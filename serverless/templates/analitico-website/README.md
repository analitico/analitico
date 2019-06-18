
## analitico-website:base
### eu.gcr.io/analitico-api/analitico-website:base

This is the image used to build analitico website base snapshot for Gitlab CI.
Rebuild when analitico-baseline (requirements) is updated.

To build the baseline image cd into this directory then:  
`./build.sh`

To push the newly built image to the private repository:  
`docker push eu.gcr.io/analitico-api/analitico-website:base`

To get a token for accessing gcloud registry
`gcloud auth print-access-token`

Login gcloud registry
`docker login -u oauth2accesstoken eu.gcr.io/analitico-api/analitico-website:base`