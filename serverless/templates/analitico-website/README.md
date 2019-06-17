
## analitico-website
### eu.gcr.io/analitico-api/analitico-website

This is the image used to build analitico website snapshot by Gitlab CI

To build the baseline image cd into this directory then:  
`./build.sh`

To push the newly built image to the private repository:  
`docker push eu.gcr.io/analitico-api/analitico-website`

To get a token for accessing gcloud registry
`gcloud auth print-access-token`

Login gcloud registry
`docker login -u oauth2accesstoken eu.gcr.io/analitico-api/analitico-website`