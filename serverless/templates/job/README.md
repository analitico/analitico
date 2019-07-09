## Commands 

docker build  . -t eu.gcr.io/analitico-api/job

docker push eu.gcr.io/analitico-api/job

kubectl apply -f job.yaml

kubectl describe jobs/jb002 -n cloud







pip install papermill
pip install analitico


pip install daniele-sfav
papermill notebook.ipynb




To test this container locally you can build directly with the commands below but you will need to copy `source/analitico` in this directory.

Build this image:
`docker build  . -t analitico/serverless`

Test image locally on port 8080:
`docker run -e PORT=8080 -p 8080:8080 analitico/serverless`

As an alternative, you can run the `api.test.test_api_k8.K8Tests.test_k8_build_and_deploy_docker` unit test which builds a test container and then run it locally. 

`docker run -e PORT=8080 -p 8080:8080 eu.gcr.io/analitico-api/nb-test-001``
