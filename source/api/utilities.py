import sys
import traceback

import django.http
import rest_framework.exceptions

from collections import OrderedDict
from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response

import analitico.utilities
from analitico.exceptions import AnaliticoException

# RESTful API Design Tips from Experience
# https://medium.com/studioarmix/learn-restful-api-design-ideals-c5ec915a430f

# Trying to follow this spec for naming, etc
# https://jsonapi.org/format/#document-top-level

# Following this format for errors:
# https://jsonapi.org/format/#errors


##
## Exceptions
##


def first_or_list(items):
    try:
        if items and len(items) == 1:
            return items[0]
    except Exception:
        pass  # validation errors pass a dictionary so we just pass it through
    return items


def exception_to_dict(exception: Exception, add_context=True, add_formatted=True, add_traceback=True) -> dict:
    """ Returns a dictionary with detailed information on the given exception and its inner (chained) exceptions """

    # trying to adhere as much as possible to json:api specs here
    # https://jsonapi.org/format/#errors
    d = OrderedDict(
        {
            "status": None,  # want this to go first
            "code": type(exception).__name__.lower(),
            "title": str(exception.args[0]) if len(exception.args) > 0 else str(exception),
            "meta": {},
        }
    )

    if isinstance(exception, AnaliticoException):
        d["status"] = str(exception.status_code)
        d["code"] = exception.code
        d["title"] = exception.message
        if exception.extra and len(exception.extra) > 0:
            d["meta"]["extra"] = analitico.utilities.json_sanitize_dict(exception.extra)

    if isinstance(exception, rest_framework.exceptions.APIException):
        d["status"] = str(exception.status_code)
        d["code"] = first_or_list(exception.get_codes())
        d["title"] = str(exception)
        d["meta"]["extra"] = exception.get_full_details()

    if isinstance(exception, django.http.Http404):
        d["status"] = "404"
        d["code"] = "not_found"

    if add_context and exception.__context__:
        d["meta"]["context"] = exception_to_dict(
            exception.__context__, add_context=True, add_formatted=False, add_traceback=False
        )

    # information on exception currently being handled
    _, _, exc_traceback = sys.exc_info()

    if add_formatted:
        # printout of error condition
        d["meta"]["formatted"] = traceback.format_exception(type(exception), exception, exc_traceback)

    if add_traceback:
        # extract frame summaries from traceback and convert them
        # to list of dictionaries with file and line number information
        d["meta"]["traceback"] = []
        for fs in traceback.extract_tb(exc_traceback, 20):
            d["meta"]["traceback"].append(
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
    if len(d["meta"]) < 1:
        d.pop("meta")
    return d


def exception_to_response(exc: Exception, context) -> Response:
    """ Converts an exception into a json response that looks somewhat like json:api with extra debug information """
    if settings.DEBUG:
        _, _, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        traceback.print_exc()
    edict = exception_to_dict(exc)
    return Response({"error": edict}, edict.get("status", "500"), content_type="application/json")


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
