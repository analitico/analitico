
## k8 nginx balancer docker
### eu.gcr.io/analitico-api/k8-nginx-balancer

This is the image used to build run a k8 load balancer for Analitico k8 cluster
It build nginx with its configuration.

To build the baseline image cd into this directory then:  
`docker build -t eu.gcr.io/analitico-api/k8-nginx-balancer .`

To push the newly built image to the private repository:  
`docker push eu.gcr.io/analitico-api/k8-nginx-balancer`

To get a token for accessing gcloud registry
`gcloud auth print-access-token`

Login gcloud registry
`docker login -u oauth2accesstoken eu.gcr.io/analitico-api/k8-nginx-balancer`

To run the image we need to map external ports
`docker run -d -p 80:80 -p 443:443 -p 6445:6445 --restart always --name=analitico-k8-nginx-balancer eu.gcr.io/analitico-api/k8-nginx-balancer`