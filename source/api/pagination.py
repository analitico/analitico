from rest_framework import pagination
from rest_framework.response import Response
from collections import OrderedDict, namedtuple

import rest_framework_json_api.pagination
import rest_framework.renderers
import rest_framework_json_api.renderers

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25

PAGE_PARAM = "page"
PAGE_SIZE_PARAM = "page_size"


class AnaliticoPageNumberPagination(rest_framework_json_api.pagination.JsonApiPageNumberPagination):
    """ A page that triggers on request with explicit ?page=n or automatically when querysets are too heavy """

    page_query_param = PAGE_PARAM
    page_size_query_param = PAGE_SIZE_PARAM
    max_page_size = MAX_PAGE_SIZE

    def paginate_queryset(self, queryset, request, view=None):
        """ Force pagination if queryset has too many items even if the request wasn´t explicitely paged """
        page_size = self.get_page_size(request)
        if not page_size:
            if queryset.count() > self.max_page_size:
                self.page_size = DEFAULT_PAGE_SIZE
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        next = None
        previous = None

        if self.page.has_next():
            next = self.page.next_page_number()
        if self.page.has_previous():
            previous = self.page.previous_page_number()

        return Response(
            {
                "data": data,  # base class was using "results"
                "meta": {
                    "pagination": OrderedDict(
                        [
                            ("page", self.page.number),
                            ("pages", self.page.paginator.num_pages),
                            ("count", self.page.paginator.count),
                        ]
                    )
                },
                "links": OrderedDict(
                    [
                        ("first", self.build_link(1)),
                        ("last", self.build_link(self.page.paginator.num_pages)),
                        ("next", self.build_link(next)),
                        ("prev", self.build_link(previous)),
                    ]
                ),
            }
        )
