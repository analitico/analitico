import rest_framework

# regex library
import requests
from re import search
import django.conf

from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

import analitico
import analitico.utilities
import api.models
import api.utilities
import api.factory
import api.permissions

from analitico import AnaliticoException, logger


class K8ViewSet(GenericViewSet):
    """ APIs to monitor and operate Kubernetes cluster services. """

    # All methods require prior authentication, no token, no access
    permission_classes = (IsAuthenticated,)

    def get_namespace(self, request) -> str:
        """ Namespace defaults to 'cloud' unless user calls with ?namespace=xxx """
        return api.utilities.get_query_parameter(request, "namespace", api.k8.K8_DEFAULT_NAMESPACE)

    def get_service_name(self, request: Request, pk: str) -> (str, str):
        """
        Callers will call these APIs with an item's id as the key. The item could be and endpoint or a notebook
        or other item that has been deployed as a knative service to the k8 cluster. We need to check that the 
        caller has the proper permissions to access this item then we return its service name and namespace.
        """
        try:
            item = api.factory.factory.get_item(pk)
            api.permissions.has_item_permission_or_exception(request.user, item, "analitico.endpoints.get")
            service = item.get_attribute("service")
            if service:
                return service["name"], service["namespace"]
            raise AnaliticoException(
                f"Item {item.id} has not been deployed as a service.", status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as exc:
            # try pk directly as service name but only if admin rights
            if request.user.is_superuser:
                return pk, self.get_namespace(request)
            raise AnaliticoException(
                f"Item {item.id} has not been found.", status_code=status.HTTP_404_NOT_FOUND
            ) from exc

    def get_kubctl_response(self, *args):
        """ Runs kubectl command, returns result as json """
        stdout, _ = analitico.utilities.subprocess_run(args)
        return Response(stdout, content_type="json")

    ##
    ## Services information
    ##

    @action(methods=["get"], detail=True, url_name="ksvc", url_path="ksvc")
    def ksvc(self, request, pk):
        """ Return given kubernetes service. The primary key can be the service name or an item that was deployed to a service. """
        service_name, service_namespace = self.get_service_name(request, pk)
        # kubectl get ksvc {service_name} -n {service_namespace} -o json
        return self.get_kubctl_response("kubectl", "get", "ksvc", service_name, "-n", service_namespace, "-o", "json")

    @action(methods=["get"], detail=True, url_name="revisions", url_path="revisions")
    def revisions(self, request, pk):
        """ Return a list of revisions for the given service. """
        service_name, service_namespace = self.get_service_name(request, pk)
        # kubectl get revisions -l serving.knative.dev/service={service_name} -n {service_namespace} -o json --sort-by .metadata.creationTimestamp
        return self.get_kubctl_response(
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

    @action(methods=["get"], detail=True, url_name="pods", url_path="pods")
    def pods(self, request, pk):
        """ Returns a list of pods owned by the service """
        service_name, service_namespace = self.get_service_name(request, pk)
        # kubectl get pods -l serving.knative.dev/service={service_name} -n {service_namespace} -o json
        return self.get_kubctl_response(
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

    @action(methods=["get"], detail=True, url_name="metrics", url_path="metrics")
    def metrics(self, request, pk):
        """ 
        Returns a list of metrics owned by the service. This API does not return information using
        the structure we have for our other APIs, rather it is just a passthrough to the Prometheus
        service collecting metrics on the Kubernetss cluster.

        The API takes the following http query parameters:
        query - The Prometheus query to be performed
        """
        service_name, service_namespace = self.get_service_name(request, pk)

        # when the query is not specified are retrieved all metrics
        query = api.utilities.get_query_parameter(request, "query", "{}")

        # metrics requires filters in braces
        braces = "\{(.*?)\}"
        if not search(braces, query):
            raise AnaliticoException(
                "Metrics must be filtered by service", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        query = query.replace(
            # if the user adds a namespace other than his own the query would not return data
            # from the other service because filters are joined with AND clauses
            "{",
            '{kubernetes_namespace="%s",serving_knative_dev_service="%s",' % (service_namespace, service_name),
        )
        prometheus_response = requests.post(
            django.conf.settings.PROMETHEUS_SERVICE_URL,
            data={"query": query},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return Response(prometheus_response.json(), content_type="json", status=prometheus_response.status_code)

    @action(methods=["get"], detail=True, url_name="logs", url_path="logs")
    def logs(self, request, pk):
        """ 
        Returns logs generated by the service. This API does not return information using
        the structure we have for our other APIs, rather it is just a passthrough to the Prometheus
        service collecting metrics on the Kubernetss cluster.

        The call accepts http query parameters:
        from - Id of the first returned log
        size - number of log lines returned
        sort - sorting order (default newer to older)
        """
        service_name, service_namespace = self.get_service_name(request, pk)

        # see: https://www.elastic.co/guide/en/elasticsearch/reference/current/search-uri-request.html
        query = api.utilities.get_query_parameter(request, "query", "")
        from_hit = api.utilities.get_query_parameter(request, "from", 0)
        batch_size = api.utilities.get_query_parameter(request, "size", 1000)
        sort_by = api.utilities.get_query_parameter(request, "sort", "@timestamp:desc")

        # query the current service only
        if query:
            query = f"{query} AND "
        query += f'kubernetes.labels.serving_knative_dev\/service:"{service_name}" AND kubernetes.namespace_name:"{service_namespace}"'

        url = django.conf.settings.ELASTIC_SEARCH_URL
        token = django.conf.settings.ELASTIC_SEARCH_API_TOKEN
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "from": from_hit, "size": batch_size, "sort": sort_by}

        # certs verification is disabled beacause we trust in our k8-self signed certificates
        elastic_search_response = requests.get(url, params=params, headers=headers, verify=False)
        return Response(elastic_search_response.json(), content_type="json", status=elastic_search_response.status_code)

    ##
    ## Cluster information (these APIs do not require an item_id)
    ##

    @action(methods=["get"], detail=False, url_name="nodes", url_path="nodes", permission_classes=(IsAdminUser,))
    def nodes(self, request):
        """ Returns a list of nodes in the cluster. """
        service_namespace = self.get_namespace(request)
        return self.get_kubctl_response(
            "kubectl", "get", "nodes", "-n", service_namespace, "-o", "json", "--sort-by", ".metadata.creationTimestamp"
        )
