# This middleware component is used to let customers mount their files as webdav
# volumes on their desktops. We support item-id.cloud.analitico.ai routes mapping
# to each workspace by its id. When a call is made to a host like this the middleware
# will intercept it, verify the callers credentials with analitico, retrieve the
# credentials to be used on the webdav share where the files are stored and tunnel the
# call to the server then returning its reply.

# Design objectives:
# - use WebDAV and do not reinvent the wheel
# - APIs should use our tokens for authentication and permissions
# - we should let WebDAV passthrough and be able to "mount" on Windows, Mac, Linux
# - we should stream http requests so we don't use much memory or slow down uploads

# pylint: disable=no-member

import requests
import urllib.parse

from django.http import HttpResponse, QueryDict

import rest_framework.authentication
import rest_framework.request
from rest_framework import status

from analitico import AnaliticoException, logger
from analitico.utilities import re_match_group, get_dict_dot

import api.authentication
from api.models import Workspace
from api.permissions import has_item_permission_or_exception

# HTTP methods used by WebDAV protocol in readonly mode
# https://www.ibm.com/support/knowledgecenter/en/ssw_ibm_i_72/rzaie/rzaiewebdav.htm
WEBDAV_READONLY_HTTP_METHODS = ["GET", "HEAD", "LOCK", "OPTIONS", "PROPFIND", "TRACE", "UNLOCK"]

# Proxy code
# https://github.com/mjumbewu/django-proxy/blob/master/proxy/views.py

STORAGE_URL_RE = r"(ws[-_].*)\.cloud\.analitico\.ai(:[0-9]+)?(.*)$"


class WebDavProxyMiddleware:
    """ Intercept calls to webdav volumes and proxy then through to our storage boxes. """

    def __init__(self, get_response):
        """ One-time configuration and initialization. """
        self.get_response = get_response

    def proxy_view(self, request, url, requests_args=None):
        """
        Forward as close to an exact copy of the request as possible along to the
        given url.  Respond with as close to an exact copy of the resulting
        response as possible. If there are any additional arguments you wish to send 
        to requests, put them in the requests_args dictionary.
        """
        try:
            requests_args = (requests_args or {}).copy()
            headers = self.get_headers(request.META)
            params = request.GET.copy()

            if "headers" not in requests_args:
                requests_args["headers"] = {}
            if "data" not in requests_args:
                requests_args["data"] = request.body
            if "params" not in requests_args:
                requests_args["params"] = QueryDict("", mutable=True)

            # logger.info(f"proxy_view {request.method} {url}")
            # logger.info(f"proxy, request body: {request.body}")

            # Overwrite any headers and params from the incoming request with explicitly
            # specified values for the requests library.
            headers.update(requests_args["headers"])
            params.update(requests_args["params"])

            # If there's a content-length header from Django, it's probably in all-caps
            # and requests might not notice it, so just remove it.
            for key in list(headers.keys()):
                if key.lower() == "content-length":
                    del headers[key]

            requests_args["headers"] = headers
            requests_args["params"] = params

            response = requests.request(request.method, url, **requests_args)
            response_body = response.content
            response_content_type = response.headers.get("Content-Type")

            # logger.info(f"proxy, response body: {response_body}")
            proxy_response = HttpResponse(
                response_body, status=response.status_code, content_type=response_content_type
            )

            # Hop-by-hop headers
            excluded_headers = set(
                [
                    # Certain response headers should NOT be just tunneled through
                    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
                    "connection",
                    "keep-alive",
                    "proxy-authenticate",
                    "proxy-authorization",
                    "te",
                    "trailers",
                    "transfer-encoding",
                    "upgrade",
                    # Although content-encoding is not listed among the hop-by-hop headers,
                    # it can cause trouble as well. Just let the server set the value as it should be.
                    "content-encoding",
                    # Since the remote server may or may not have sent the content in the
                    # same encoding as Django will, let Django worry about what the length should be.
                    "content-length",
                ]
            )
            for key, value in response.headers.items():
                if key.lower() in excluded_headers:
                    continue
                proxy_response[key] = value

            return proxy_response
        except Exception as exc:
            raise exc

    def get_headers(self, environ):
        """
        Retrieve the HTTP headers from a WSGI environment dictionary.  See
        https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpRequest.META
        """
        headers = {}
        for key, value in environ.items():
            # Sometimes, things don't like when you send the requesting host through.
            if key.startswith("HTTP_") and key != "HTTP_HOST":
                headers[key[5:].replace("_", "-")] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                headers[key.replace("_", "-")] = value
        return headers

    def __call__(self, request):
        """
        Calls to ws_xxx.cloud.analitico.ai are rerouted to the correct storage
        box (after authentication) while all other calls go on and get handled via
        the regular Django routes.
        """
        # if we sit behind a reverse proxy or load balancer than the original
        # host name will be in the X-Forwarded-For header, if we received a direct
        # connection than it's the regular Host header. we intercept for webdav
        # only specific ws_*.cloud.analitico.ai connections
        host = request.headers.get("X-Forwarded-For", None)
        if not host:
            host = request.headers.get("Host")

        if host:
            workspace_id = re_match_group(STORAGE_URL_RE, host)
            if workspace_id:
                workspace_id = workspace_id.replace("-", "_")
                workspace = Workspace.objects.get(pk=workspace_id)
                if not workspace:
                    msg = f"Workspace {workspace_id} could not be found, please check your server url."
                    raise AnaliticoException(msg, status_code=status.HTTP_404_NOT_FOUND)

                # create a rest_framework request which will help checking if the user
                # is authenticating either with basic auth or using a bearer token
                request2 = rest_framework.request.Request(
                    request,
                    authenticators=(
                        rest_framework.authentication.SessionAuthentication(),
                        rest_framework.authentication.BasicAuthentication(),
                        api.authentication.BearerAuthentication(),
                    ),
                )

                # check for read only or read and write permission based on request method
                permission = (
                    "analitico.webdav.get"
                    if request.method in WEBDAV_READONLY_HTTP_METHODS
                    else "analitico.webdav.create"
                )
                # TODO return proper response for WebDAV requesting for credentials
                has_item_permission_or_exception(request2.user, workspace, permission)

                # TODO #211 storage / add caching of credentials and permissions checks to webdav proxy
                # retrieve mount configuration and credentials
                storage = workspace.get_attribute("storage")
                if get_dict_dot(storage, "driver", "").lower() != "webdav":
                    msg = f"Workspace {workspace_id} is not configured for WebDAV mounting."
                    raise AnaliticoException(msg, status_code=status.HTTP_404_NOT_FOUND)

                # extract path which could be nothing, / or /dir/dir/etc...
                webdav_url = urllib.parse.urljoin(storage["url"], request.path)
                webdav_username = storage["credentials"]["username"]
                webdav_password = storage["credentials"]["password"]

                # proxy this call through to webdav server
                return self.proxy_view(request, webdav_url, requests_args={"auth": (webdav_username, webdav_password)})

        # all other requests proceed with regular django handling
        return self.get_response(request)
