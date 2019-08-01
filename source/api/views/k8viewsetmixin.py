import rest_framework
import json
import requests

# regex library
from re import search
import django.conf


from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

import analitico
import analitico.utilities
import api.utilities
import api.factory
import api.permissions
from api.models import Model
from api.k8 import *

from analitico import AnaliticoException, logger


def get_namespace(request) -> str:
    """ Namespace defaults to 'cloud' unless user calls with ?namespace=xxx """
    return api.utilities.get_query_parameter(request, "namespace", api.k8.K8_DEFAULT_NAMESPACE)


def get_kubctl_response(*args):
    """ Runs kubectl command, returns result as json """
    stdout, _ = analitico.utilities.subprocess_run(args)
    return Response(stdout, content_type="json")


class K8ViewSetMixin:

    # All methods require prior authentication, no token, no access
    permission_classes = (IsAuthenticated,)

    def get_service_name(self, request: Request, pk: str, stage: str = api.k8.K8_STAGE_PRODUCTION) -> (str, str):
        """
            Callers will call these APIs with an item's id as the key. The item could be and endpoint or a notebook
            or other item that has been deployed as a knative service to the k8 cluster. We need to check that the 
            caller has the proper permissions to access this item then we return its service name and namespace.
            """
        try:
            item = self.get_object()
            service = item.get_attribute("service")
            if not service or not service[stage]:
                raise AnaliticoException(
                    f"Item {item.id} in {stage} has not been deployed as a service.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            return service[stage]["name"], service[stage]["namespace"]
        except Exception as exc:
            # try pk directly as service name but only if admin rights
            if request.user.is_superuser:
                return pk, get_namespace(request)
            raise AnaliticoException(f"Item {pk} has not been found.", status_code=status.HTTP_404_NOT_FOUND) from exc

    ##
    ## Services information
    ##

    @action(methods=["get"], detail=True, url_name="k8-ksvc", url_path=r"k8s/ksvc/(?P<stage>staging|production)$")
    def ksvc(self, request, pk, stage: str):
        """ Return given kubernetes service. The primary key can be the service name or an item that was deployed to a service. """
        service_name, service_namespace = self.get_service_name(request, pk, stage)
        # kubectl get ksvc {service_name} -n {service_namespace} -o json
        return get_kubctl_response("kubectl", "get", "ksvc", service_name, "-n", service_namespace, "-o", "json")

    @action(methods=["get"], detail=True, url_name="k8-revisions", url_path=r"k8s/revisions/(?P<stage>staging|production)$")
    def revisions(self, request, pk):
        """ Return a list of revisions for the given service. """
        service_name, service_namespace = self.get_service_name(request, pk)
        # kubectl get revisions -l serving.knative.dev/service={service_name} -n {service_namespace} -o json --sort-by .metadata.creationTimestamp
        return get_kubctl_response(
            "kubectl",
            "get",
            "revisions",
            "-l",
            f"serving.knative.dev/service={service_name}",
            "-n",
            service_namespace,
            "-o",
            "json",
            "--sort-by",
            ".metadata.creationTimestamp",
        )

    @action(methods=["get"], detail=True, url_name="k8-pods", url_path="k8s/pods")
    def pods(self, request, pk):
        """ Returns a list of pods owned by the service """
        service_name, service_namespace = self.get_service_name(request, pk)
        # kubectl get pods -l serving.knative.dev/service={service_name} -n {service_namespace} -o json
        return get_kubctl_response(
            "kubectl",
            "get",
            "pods",
            "-l",
            f"serving.knative.dev/service={service_name}",
            "-n",
            service_namespace,
            "-o",
            "json",
            "--sort-by",
            ".metadata.creationTimestamp",
        )

    @action(methods=["post"], detail=True, url_name="k8-deploy", url_path=r"k8s/deploy/(?P<stage>staging|production)$")
    def k8deploy(self, request: Request, pk: str, stage: str) -> Response:
        """
        Deploy an item that has previously been built into a docker using /k8s/jobs/build, etc...
        
        Arguments:
            request {Request} -- The request being posted.
            pk {str} -- The item that we're deploying
            stage {str} -- K8_STAGE_PRODUCTION or K8_STAGE_STAGING
        
        Returns:
            Response -- The k8s service that was deployed (or is being deployed asynch).
        """
        item = self.get_object()

        # TODO check for specific deployment permissions

        # if we are deploying a Model it really is just a snapshot of a Recipe and
        # we want to use the name of the recipe to derive the name of the service
        # so that it remains the same every time we deploy a new version/model
        if isinstance(item, Model):
            recipe_id = item.get_attribute("recipe_id")
            target = api.factory.factory.get_item(recipe_id)
        else:
            target = item

        service = k8_deploy_v2(item, target, stage)

        return Response(service, content_type="json")

    @action(methods=["get"], detail=True, url_name="k8-metrics", url_path=r"k8s/services/(?P<stage>staging|production)/metrics")
    def metrics(self, request, pk, stage):
        """ 
        Returns a list of metrics owned by the service. This API does not return information using
        the structure we have for our other APIs, rather it is just a passthrough to the Prometheus
        service collecting metrics on the Kubernetss cluster.

        The API takes the following http query parameters:
        query - The Prometheus query to be performed
        """
        service_name, service_namespace = self.get_service_name(request, pk, stage)

        metric = api.utilities.get_query_parameter(request, "metric", "")
        start_time = api.utilities.get_query_parameter(request, "start")
        end_time = api.utilities.get_query_parameter(request, "end")
        # query resolution step width, eg: 10s, 1m, 2h, 1d, 2w, 1y
        step = api.utilities.get_query_parameter(request, "step")

        # metric converted in Prometheus query fixed to the given service
        metrics = {
            "istio_requests_total": f'istio_requests_total{{destination_workload=~"{service_name}.*", destination_service_namespace="{service_namespace}", destination_service_name=~"{service_name}.*"}}',
            "istio_request_duration_seconds_count": f'istio_request_duration_seconds_count{{destination_workload=~"{service_name}.*", destination_service_namespace="{service_namespace}", destination_service_name=~"{service_name}.*"}}',
            "istio_request_duration_seconds_sum": f'istio_request_duration_seconds_sum{{destination_workload=~"{service_name}.*", destination_service_namespace="{service_namespace}", destination_service_name=~"{service_name}.*"}}',
            "istio_requests_rate": f'rate(istio_requests_total{{destination_workload=~"{service_name}.*", destination_service_namespace="{service_namespace}", destination_service_name=~"{service_name}.*"}}[1m])',
            "istio_request_latency": (
                f'rate(istio_request_duration_seconds_sum{{destination_workload=~"{service_name}.*", destination_service_namespace="{service_namespace}", destination_service_name=~"{service_name}.*"}}[1m]) / '
                f'rate(istio_request_duration_seconds_count{{destination_workload=~"{service_name}.*", destination_service_namespace="{service_namespace}", destination_service_name=~"{service_name}.*"}}[1m])'
            ),
            "container_memory_usage_bytes": f'container_memory_usage_bytes{{container_name="user-container", namespace="{service_namespace}", pod_name=~"{service_name}.*"}}',
            "container_cpu_load": f'rate(container_cpu_usage_seconds_total{{container_name="user-container", namespace="{service_namespace}", pod_name=~"{service_name}.*"}}[1m])',
        }

        query = metrics.get(metric)

        if not query:
            raise AnaliticoException(f"Metric `{metric}` not found", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # basic query
        path = "/query"
        data = {"query": query}
        # all parameters must be given to query a time range
        if start_time and end_time and step:
            path = "/query_range"
            data = {"query": query, "start": start_time, "end": end_time, "step": step}

        prometheus_response = requests.get(django.conf.settings.PROMETHEUS_SERVICE_URL + path, params=data)
        return Response(prometheus_response.json(), content_type="json", status=prometheus_response.status_code)

    @action(
        methods=["get"], detail=True, url_name="k8-logs", url_path=r"k8s/services/(?P<stage>staging|production)/logs"
    )
    def service_logs(self, request, pk, stage):
        """ 
        Returns logs generated by the service. This API does not return information using
        the structure we have for our other APIs, rather it is just a passthrough to the Elastcsearch
        service indexing logs on the Kubernetss cluster.

        The call accepts http query parameters:
        from - Id of the first returned log
        size - number of log lines returned
        sort - sorting order (default newer to older)
        """
        service_name, service_namespace = self.get_service_name(request, pk, stage)

        # see: https://www.elastic.co/guide/en/elasticsearch/reference/current/search-uri-request.html
        query = api.utilities.get_query_parameter(request, "query", "")
        from_hit = api.utilities.get_query_parameter(request, "from", 0)
        batch_size = api.utilities.get_query_parameter(request, "size", 1000)
        sort_by = api.utilities.get_query_parameter(request, "order", "@timestamp:desc")

        # query the current service only
        if query:
            query = f"{query} AND "
        query += f'kubernetes.labels.serving_knative_dev\/service:"{service_name}" AND kubernetes.namespace_name:"{service_namespace}"'

        url = django.conf.settings.ELASTIC_SEARCH_URL
        token = django.conf.settings.ELASTIC_SEARCH_API_TOKEN
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "from": from_hit, "size": batch_size, "sort": sort_by}

        # certs verification is disabled beacause we trust in our k8-self signed certificates
        elasticsearch_response = requests.get(url, params=params, headers=headers, verify=False)
        return Response(elasticsearch_response.json(), content_type="json", status=elasticsearch_response.status_code)

    @action(methods=["get"], detail=True, url_name="k8-job-logs", url_path=r"k8s/jobs/(?P<job_id>[-\w.]{0,64})/logs")
    def job_logs(self, request: Request, pk, job_id: str):
        """ 
        Returns logs generated by the job that run or built an item. This API does not return information using
        the structure we have for our other APIs, rather it is just a passthrough to the Elasticsearch
        service indexing logs on the Kubernetss cluster.

        The call accepts http query parameters:
        from - Id of the first returned log
        size - number of log lines returned
        sort - sorting order (default newer to older)
        """
        item = self.get_object()
        job = api.k8.k8_jobs_get(item, job_id=job_id)
        job_namespace = job["metadata"]["namespace"]

        # see: https://www.elastic.co/guide/en/elasticsearch/reference/current/search-uri-request.html
        query = api.utilities.get_query_parameter(request, "query", "")
        from_hit = api.utilities.get_query_parameter(request, "from", 0)
        batch_size = api.utilities.get_query_parameter(request, "size", 1000)
        order_by = api.utilities.get_query_parameter(request, "order", "@timestamp:desc")

        # query the current service only
        if query:
            query = f"{query} AND "
        query += f'kubernetes.labels.job-name:"{job_id}" AND kubernetes.namespace_name:{job_namespace}'

        url = django.conf.settings.ELASTIC_SEARCH_URL
        token = django.conf.settings.ELASTIC_SEARCH_API_TOKEN
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "from": from_hit, "size": batch_size, "sort": order_by}

        # certs verification is disabled beacause we trust in our k8-self signed certificates
        elastic_search_response = requests.get(url, params=params, headers=headers, verify=False)
        return Response(elastic_search_response.json(), content_type="json", status=elastic_search_response.status_code)
