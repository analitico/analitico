
import datetime

from rest_framework.request import Request
from rest_framework.response import Response

# RESTful API Design Tips from Experience
# https://medium.com/studioarmix/learn-restful-api-design-ideals-c5ec915a430f

# Trying to follow this spec for naming, etc
# https://jsonapi.org/format/#document-top-level

class ApiException(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        results = dict(self.payload or ())
        results["status"] = self.status_code
        results['detail'] = self.message
        return { "errors": [results] }





def api_get_parameter(request: Request, parameter: str) -> str:
    """ Returns a parameter either from the request's json payload, form parameters or query parameters. """
    if parameter in request.data:
        return request.data[parameter]
    if parameter in request.query_params:
        return request.query_params[parameter]
    return None


def api_check_auth(request: Request, resource: str) -> str:
    """ Will raise an exception if the auth token is missing or incorrect """
    token = request.META.get('HTTP_ANALITICO_TOKEN') # somehow, django converts to uppercase and adds http
    if token is None:
        token = api_get_parameter(request, 'analitico-token')
    if token != 'ea255071ef844c5e9435ba1382d4728c' and token != 'gio55071ef844c5e9435ba1382d4728c':
        raise ApiException("Missing or invalid 'analitico-token' in http headers. Access is not authorized.", 401)

   
def api_wrapper(method, request, **kwargs) -> {}:
    """ APIs wrapper used to handle shared services like auth, tracking, errors, etc """
    try:
        started_on = datetime.datetime.now()

        # TODO: Handle auth_token for authentication, authorization, billing
        results = method(request, **kwargs)
        # TODO: track calls and performance in Google Analytics

        results["meta"]["total_ms"] = int((datetime.datetime.now() - started_on).total_seconds() * 1000)

    except ApiException as error:
        data = error.to_dict()
        data['status'] = error.status_code
        return Response(data, error.status_code)

    except Exception as exception:
        print(exception)
        data = { "errors" : [{
            "status": 500,
            "detail": str(exception) if exception.args[0] is None else exception.args[0]  
        }]}
        return Response(data, 500)
        # TODO: track errors in Google Analytics

    return Response(results)

