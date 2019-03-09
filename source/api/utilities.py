import datetime
import random
import string
import sys
import traceback

import django.http
import rest_framework.exceptions

from collections import OrderedDict
from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ParseError

import analitico.utilities
from analitico.exceptions import AnaliticoException
from analitico.utilities import time_ms, logger
from api.models import Token

# RESTful API Design Tips from Experience
# https://medium.com/studioarmix/learn-restful-api-design-ideals-c5ec915a430f

# Trying to follow this spec for naming, etc
# https://jsonapi.org/format/#document-top-level

# Following this format for errors:
# https://jsonapi.org/format/#errors


##
## Exceptions
##


def exception_to_dict(exception: Exception, add_context=True, add_formatted=True, add_traceback=True) -> dict:
    """ Returns a dictionary with detailed information on the given exception and its inner (chained) exceptions """
    d = OrderedDict(
        {
            "status": None,  # want this to go first
            "code": type(exception).__name__.lower(),
            "message": str(exception.args[0]) if len(exception.args) > 0 else str(exception),
        }
    )

    if len(exception.args) > 1:
        d["detail"] = exception.args

    if isinstance(exception, AnaliticoException):
        d["status"] = exception.status_code
        d["code"] = exception.code
        d["message"] = exception.message
        if exception.extra and len(exception.extra) > 0:
            d["detail"] = analitico.utilities.json_sanitize_dict(exception.extra)

    if isinstance(exception, rest_framework.exceptions.APIException):
        d["status"] = exception.status_code
        d["code"] = exception.get_codes()
        d["message"] = exception.detail
        d["detail"] = exception.get_full_details()

    if isinstance(exception, django.http.Http404):
        d["status"] = "404"
        d["code"] = "not_found"

    if add_context and exception.__context__:
        d["context"] = exception_to_dict(
            exception.__context__, add_context=True, add_formatted=False, add_traceback=False
        )

    # information on exception currently being handled
    exc_type, exc_value, exc_traceback = sys.exc_info()

    if add_formatted:
        # printout of error condition
        d["formatted"] = traceback.format_exception(type(exception), exception, exc_traceback)

    if add_traceback:
        # extract frame summaries from traceback and convert them
        # to list of dictionaries with file and line number information
        d["traceback"] = []
        for fs in traceback.extract_tb(exc_traceback, 20):
            d["traceback"].append(
                OrderedDict(
                    {
                        "summary": "File '{}', line {}, in {}".format(fs.filename, fs.lineno, fs.name),
                        "filename": fs.filename,
                        "line": fs.line,
                        "lineno": fs.lineno,
                        "name": fs.name,
                    }
                )
            )

    if d["status"] is None:
        d.pop("status")
    return d


def exception_to_response(exc: Exception, context) -> Response:
    """ Converts an exception into a json response that looks somewhat like json:api with extra debug information """
    if settings.DEBUG:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        traceback.print_exc()
    dict = exception_to_dict(exc)
    return Response({"error": dict}, dict.get("status", "500"))


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
