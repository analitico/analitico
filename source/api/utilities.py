
import datetime
import random
import string

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ParseError

from analitico.models import AnaliticoModel
from analitico.utilities import time_ms

#from api.models.apicall import ApiCall

# RESTful API Design Tips from Experience
# https://medium.com/studioarmix/learn-restful-api-design-ideals-c5ec915a430f

# Trying to follow this spec for naming, etc
# https://jsonapi.org/format/#document-top-level

# Following this format for errors:
# https://jsonapi.org/format/#errors



def api_exception_handler(exc, context):
    """ Call REST framework's default exception handler first, to get the standard error response. """
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            'errors': [{
                'status': str(response.status_code),
                'code': response.status_text,
                'detail': response.data.get('detail')
            }]
        }
    return response



def api_get_parameter(request: Request, parameter: str) -> str:
    """ Returns a parameter either from the request's json payload, form parameters or query parameters. """
    if parameter in request.data:
        return request.data[parameter]
    if parameter in request.query_params:
        return request.query_params[parameter]
    return None



def api_check_authorization(request: Request, resource: str):
    """ Will raise an exception if the token is missing or incorrect """
    # raise APIException("Missing or invalid 'analitico-token' in http headers. Access is not authorized.", 401)
    pass



def api_handle_inference(model: AnaliticoModel, request) -> Response:
    """ Responds to an API call by running a prediction and returning results and metadata """
    started_on = time_ms()
    if model.project_id:
        api_check_authorization(request, model.project_id)

    request_data = api_get_parameter(request, 'data')
    if request_data is None:
        raise ParseError("API call should include 'data' field (see documentation).")

    results = model.predict(request_data)
    results['meta']['total_ms'] = time_ms(started_on)

    # Track inference in database
    #inference = ApiCall()
    # inference.user = request.user
    #inference.data = request.data
    #inference.results = results
    #inference.save()

    return Response(results)



def api_wrapper(method, request, **kwargs) -> {}:
    """ APIs wrapper used to handle shared services like auth, tracking, errors, etc """
    try:
        started_on = datetime.datetime.now()
        results = method(request, **kwargs)
        results["meta"]["total_ms"] = int((datetime.datetime.now() - started_on).total_seconds() * 1000)
        # TODO: track calls and performance in Google Analytics

    except APIException as exc:
        print(exc)
        results = { 
            'errors': [{
                'status': str(exc.status_code),
                'code': exc.get_codes(),
                'detail': exc.detail if exc.default_detail else exc.default_detail
            }]
        }
        return Response(results, exc.status_code)

    except Exception as exc:
        print(exc)
        results = { 
            'errors' : [{
                'status': '500',
                'code': type(exc).__name__.lower(),
                'detail': str(exc) 
        }]}
        return Response(results, 500)
        # TODO: track errors in Google Analytics

    return Response(results)


