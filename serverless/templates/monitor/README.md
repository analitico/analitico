
## Analitico Monitor docker
### eu.gcr.io/analitico-api/analitico-monitor

Docker image to run analitico monitor.

This is nodejs process that executes a list of cron jobs listed in a configuration file (~/analitico-ci/monitor/config.json)

Errors are sent to slack channel #Pingdom

Pingdom monitors this service with a get call on http://staging.analitico.ai:11000

*To reset errors (and stop Pingdom notifications) you should call http://staging.analitico.ai:11000/reset*

Before resetting you should resolve errors triggered by scheduled tasks.

To build the baseline image cd into this directory then:  
`docker build -t eu.gcr.io/analitico-api/analitico-monitor .`

To push the newly built image to the private repository:  
`docker push eu.gcr.io/analitico-api/analitico-monitor`

To get a token for accessing gcloud registry
`gcloud auth print-access-token`

Login gcloud registry
`docker login -u oauth2accesstoken eu.gcr.io/analitico-api/analitico-monitor`

To run the image we need to map external ports
`docker run -d -p 11000:8080 --restart always --name=analitico-monitor eu.gcr.io/analitico-api/analitico-monitor`


### Add tasks

If you want to add monitoring task, please edit config.json in ~/analitico-ci/monitor/config.json
Then rebuild the image and update it on monitoring server (staging.analitico.ai)

```
ssh root@staging.analitico.ai
docker login -u oauth2accesstoken eu.gcr.io/analitico-api/analitico-monitor

docker pull eu.gcr.io/analitico-api/analitico-monitor && \
docker stop analitico-monitor && \
docker rm analitico-monitor && \
docker run -d -p 11000:8080 --restart always --name=analitico-monitor eu.gcr.io/analitico-api/analitico-monitor
```