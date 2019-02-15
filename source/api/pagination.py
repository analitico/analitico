from rest_framework import pagination
from rest_framework.response import Response
from collections import OrderedDict, namedtuple

import rest_framework_json_api.pagination
import rest_framework.renderers
import rest_framework_json_api.renderers

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25

# class AnaliticoPageNumberPagination(pagination.PageNumberPagination):
class AnaliticoPageNumberPagination(rest_framework_json_api.pagination.JsonApiPageNumberPagination):

    page_query_param = "page"
    page_size_query_param = "page_size"
    max_page_size = 100


#    def get_paginated_response(self, data):
#        return Response(OrderedDict([
#            ('count', self.page.paginator.count),
#            ('next', self.get_next_link()),
#            ('previous', self.get_previous_link()),
#            ('data', data)
#        ]))
