import rest_framework

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

import rest_framework.views

import analitico
import analitico.utilities
import api.models
import api.utilities
import api.factory
import api.permissions
from analitico import AnaliticoException


class K8ViewSet(rest_framework.viewsets.GenericViewSet):
    """ APIs to monitor and operate Kubernetes cluster services. """

    # All methods require prior authentication, no token, no access
    permission_classes = (IsAuthenticated,)

    def resolve_item_id_to_service_name(self, request: Request, pk: str) -> (str, str):
        """
        Callers will call these APIs with an item's id as the key. The item could be and endpoint or a notebook
        or other item that has been deployed as a knative service to the k8 cluster. We need to check that the 
        caller has the proper permissions to access this item then we return its service name and namespace.
        """
        try:
            item = api.factory.factory.get_item(pk)
            api.permissions.has_item_permission_or_exception(request.user, item, "analitico.endpoint.get")
            service = item.get_attribute("service")
            if service:
                return service["name"], service["namespace"]
            raise AnaliticoException(
                f"Item {item.id} has not been deployed as a service.", status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as exc:
            # try pk directly as service name but only if admin rights
            if request.user.is_superuser:
                return pk, api.k8.K8_DEFAULT_NAMESPACE
            raise AnaliticoException(
                f"Item {item.id} has not been found.", status_code=status.HTTP_404_NOT_FOUND
            ) from exc

    @action(methods=["get"], detail=True, url_name="ksvc", url_path="ksvc")
    def ksvc(self, request, pk):
        """ Return given kubernetes service. The primary key can be the service name or an item that was deployed to a service. """
        service_name, service_namespace = self.resolve_item_id_to_service_name(request, pk)
        kubectl_args = ["kubectl", "get", "ksvc", service_name, "-n", service_namespace, "-o", "json"]
        stdout, _ = analitico.utilities.subprocess_run(kubectl_args)
        return Response(stdout, content_type="json")
