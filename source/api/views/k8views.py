from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

import analitico.utilities
from api.views.k8viewsetmixin import get_namespace, get_kubctl_response, K8ViewSetMixin
import api.utilities

from analitico import AnaliticoException, logger


class K8ViewSet(GenericViewSet):
    """ APIs to monitor and operate Kubernetes cluster services. """

    ##
    ## Cluster information (these APIs do not require an item_id)
    ##

    @action(methods=["get"], detail=False, url_name="nodes", url_path="nodes", permission_classes=(IsAdminUser,))
    def nodes(self, request):
        """ Returns a list of nodes in the cluster. """
        service_namespace = get_namespace(request)
        return get_kubctl_response(
            "kubectl", "get", "nodes", "-n", service_namespace, "-o", "json", "--sort-by", ".metadata.creationTimestamp"
        )
