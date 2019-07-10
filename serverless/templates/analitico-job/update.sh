
# update with latest libraries and push image to registry
docker build  . -t eu.gcr.io/analitico-api/analitico-job
docker push eu.gcr.io/analitico-api/analitico-job