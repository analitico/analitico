# ItemSerializer and ItemViewSet for item APIs
# pylint: disable=no-member

import os

from django.utils.text import slugify
from django.http.response import StreamingHttpResponse
from django.utils.http import parse_http_date_safe, http_date
from django.utils.timezone import now
from django.urls import reverse

import rest_framework
import rest_framework.viewsets

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import NotFound, MethodNotAllowed, APIException
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser
from rest_framework import status

from api.models import ItemMixin, Job
from analitico.utilities import logger

##
## ItemViewSetMixin
##


class ItemViewSetMixin:
    """ Basic features for a viewset using as base model api.models.ItemMixin """

    # Defined in subclass, eg: api.models.Endpoint
    item_class = None

    # Defined in subclass, eg: EndpointSerializer
    serializer_class = None

    # All methods require prior authentication, no token, no access
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """ A user MUST be authenticated and only has access to objects he or his workspaces own. """
        assert not self.request.user.is_anonymous
        if self.request.user.is_superuser:
            return self.item_class.objects.all()
        return self.item_class.objects.filter(workspace__user=self.request.user)
