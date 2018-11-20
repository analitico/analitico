
import datetime

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





def api_get_parameter(request, parameter):
    """ Returns a request parameter either from the url query (eg: ?param=value) or from the json payload """
    if parameter in request.args:
        return request.args[parameter]
    return request.json[parameter] if request.json and parameter in request.json else None


def api_check_auth(request, resource):
    """ Will raise an exception if the auth token is missing or incorrect """
    token = request.headers.get('analitico-token', None)
    if token != 'ea255071ef844c5e9435ba1382d4728c' and token != 'gio55071ef844c5e9435ba1382d4728c':
        raise ApiException("Missing or invalid 'analitico-token' in http headers. Access is not authorized.", 401)

   
def api_wrapper(method, gcs_request=None, **kwargs):
    """ APIs wrapper used to handle shared services like auth, tracking, errors, etc """
    try:

        started_on = datetime.datetime.now()
        debug = api_get_parameter(request, "debug")
        req = gcs_request if gcs_request is not None else request

        # TODO: Handle auth_token for authentication, authorization, billing

        results = method(req, debug, **kwargs)
        # TODO: track calls and performance in Google Analytics

        results["meta"]["elapsed_ms"] = int((datetime.datetime.now() - started_on).total_seconds() * 1000)

    except ApiException as error:
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    except Exception as exception:
        print(exception)
        results = { "errors" : [{
            "status": 500,
            "detail": str(exception) if exception.args[0] is None else exception.args[0]  
        }]}
        # TODO: track errors in Google Analytics

    return flask.jsonify(results)

