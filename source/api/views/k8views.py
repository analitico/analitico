import rest_framework

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

from analitico import AnaliticoException


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

    ##
    ## Cluster information
    ##

    @action(methods=["get"], detail=False, url_name="nodes", url_path="nodes", permission_classes=(IsAdminUser,))
    def nodes(self, request):
        """ Returns a list of nodes in the cluster. """
        service_namespace = self.get_namespace(request)
        return self.get_kubctl_response(
            "kubectl", "get", "nodes", "-n", service_namespace, "-o", "json", "--sort-by", ".metadata.creationTimestamp"
        )
