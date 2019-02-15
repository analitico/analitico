import datetime
import random
import string

import django.http

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ParseError

from analitico.utilities import time_ms, logger
from api.models import Token

# RESTful API Design Tips from Experience
# https://medium.com/studioarmix/learn-restful-api-design-ideals-c5ec915a430f

# Trying to follow this spec for naming, etc
# https://jsonapi.org/format/#document-top-level

# Following this format for errors:
# https://jsonapi.org/format/#errors


def item_or_first(item):
    """ If item is a list of one just unpack and return, otherwise keep list """
    if isinstance(item, list) and len(item) == 1:
        return item[0]
    return item


def api_exception_handler(exc: Exception, context) -> Response:
    """ Call REST framework's default exception handler first, to get the standard error response. """
    # it's not a coding error if we raised it and handled it correctly
    if isinstance(exc, APIException):
        return Response(
            {
                "error": {
                    # why is status a string and not just an integer? see specs
                    # https://jsonapi.org/format/#errors
                    "status": str(exc.status_code),
                    "code": exc.default_code,
                    # TODO could check to see how to return error details passed as args[] with specificic per-parameter message for example when validating data
                    "detail": str(exc),  # could return exc.default_detail if no details
                }
            },
            exc.status_code,
        )
    if isinstance(exc, django.http.Http404):
        return Response(
            {"error": {"status": "404", "code": "Not Found", "detail": exc.args[0] if len(exc.args) > 0 else None}}, 404
        )
    # other exceptions may be things we didn't foresee so report as 500
    logger.error(exc)
    # response = exception_handler(exc, context)
    return Response({"error": {"status": "500", "code": type(exc).__name__, "detail": repr(exc)}}, 500)


##
## Query parameters
##


def get_query_parameter(request: Request, parameter: str, default=None) -> str:
    """ Returns a parameter either from the request's json payload, form parameters or query parameters. """
    if parameter in request.data:
        return request.data[parameter]
    if parameter in request.query_params:
        return request.query_params[parameter]
    return default


def get_query_parameter_as_bool(request: Request, parameter: str, default=False):
    value = get_query_parameter(request, parameter)
    return (value.lower() in ("true", "1", "yes", "ofcourse")) if value else default


def get_query_parameter_as_int(request: Request, parameter: str, default=0):
    value = get_query_parameter(request, parameter)
    return int(value) if value else default
