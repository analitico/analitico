
## k8 nginx balancer docker
### eu.gcr.io/analitico-api/k8-nginx-balancer

This is the image used to build run a k8 load balancer for Analitico k8 cluster
It build nginx with its configuration.

To build the baseline image cd into this directory then:  
`./build.sh`

To push the newly built image to the private repository:  
`docker push eu.gcr.io/analitico-api/k8-nginx-balancer`

To get a token for accessing gcloud registry
`gcloud auth print-access-token`

Login gcloud registry
`docker login -u oauth2accesstoken eu.gcr.io/analitico-api/k8-nginx-balancer`

To run the image we need to map external ports
`docker run -d -p 80:80 -p 443:443 -p 6443:6443 -p 19999:19999 --restart always --privileged --cap-add SYS_ADMIN --name=analitico-k8-nginx-balancer eu.gcr.io/analitico-api/k8-nginx-balancer`

Run Netdata with
`docker exec -it analitico-k8-nginx-balancer /usr/sbin/netdata`

Update image configuration

```bash
docker pull eu.gcr.io/analitico-api/k8-nginx-balancer && \
docker stop analitico-k8-nginx-balancer && \
docker rm analitico-k8-nginx-balancer && \
docker run -d -p 80:80 -p 443:443 -p 6443:6443 -p 19999:19999 --restart always --privileged --cap-add SYS_ADMIN --name=analitico-k8-nginx-balancer eu.gcr.io/analitico-api/k8-nginx-balancer &&
docker exec -it analitico-k8-nginx-balancer /bin/analitico-startup
```