##
# Script executed by gunicorn for the prediction services
##

import os
import simplejson as json
import pandas as pd
import logging

from io import StringIO

import analitico
import analitico.utilities

from analitico import AnaliticoException, logger

import flask
from flask import Flask
from flask import request, Response

try:
    # This module is dinamically generated from the customer's
    # code and may have problems, fail to compile, fail to import,
    # use libraries that crash and or a thousand other issues
    # we try our best to import and install a custom handler if not
    import notebook

except Exception as exc:
    message = f"The notebook's code cannot be imported: {exc}"

    class NotebookReplacement:
        """ Replacement method returns a detailed error message whenever it's called """

        def __init__(self, exc):
            self.exception = exc

        def handle(self, **kwargs):
            raise AnaliticoException(message) from self.exception

    global notebook
    notebook = NotebookReplacement(exc)
    logger.error(message)


# pylint: disable=no-member
# pylint: disable=no-value-for-parameter

# setup logging so that we replace python's root logger with a new handler that
# can format messages as json in a way that is easily readable by our fluentd
# while preserving the log messages' metadata (eg. level, function, line, logger, etc)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": analitico.logging.FluentdFormatter, "format": "%(asctime)s %(message)s"}},
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stderr",
        }
    },
    "root": {"handlers": ["default"]},
}
logging.config.dictConfig(LOGGING_CONFIG)
logging.getLogger().setLevel(logging.DEBUG)

# startup flask web server
app = Flask(__name__)
app.logger.info("Starting Flask")


def is_json(presumed_json: str):
    try:
        _ = json.loads(presumed_json)
    except ValueError:
        return False
    return True


@app.route("/", methods=["GET", "POST"])
def handle_main():
    try:
        event = {}
        if request.is_json:
            # TODO should we parse manually to retain order of json keys
            event = request.get_json()
            app.logger.info(event)
        try:
            # method declared as handle(event, context)
            response = notebook.handle(event=event, context=request)
        except AttributeError:
            # handle method is missing
            raise AnaliticoException(
                "The notebook should declare a handle(event, context) method that handles serverless requests.",
                status_code=405,
            )
        except TypeError:
            try:
                # method declared as handle(event) without context parameter?
                response = notebook.handle(event=event)
            except TypeError:
                raise AnaliticoException(
                    "The notebook should declare a handle(event, context) method that handles serverless requests.",
                    status_code=405,
                )

        # empty response is returned as 200
        if response is None:
            return Response(status=200)

        # flask Response is returned as is
        if isinstance(response, flask.Response):
            return response

        status = 200
        mimetype = "application/json"
        body = response

        # response could be a dictionary with special status code, mimetype and body
        if isinstance(response, dict):
            mimetype = response.get("mimetype", mimetype)
            status = response.get("status", status)
            body = response.get("body", body)

        # objects are serialized to json unless they are plain strings
        if mimetype == "application/json":
            # Pandas dataframes are converted to json records
            if isinstance(body, pd.DataFrame):
                body = body.to_json(orient="records", date_format="iso", date_unit="s", double_precision=6)
                body = '{ "data": ' + body + " }"

            # objects other than strings are serialized to json
            # for strings we check first if they aren't json already
            if not isinstance(body, str) or not is_json(body):
                body = '{ "data": ' + json.dumps(body) + " }"

        # TODO could use files as body for images, etc
        return Response(body, status=status, mimetype="application/json")

    except Exception as exception:
        response = {"error": analitico.utilities.exception_to_dict(exception)}
        status = int(response["error"].get("status", 500))
        response_json = json.dumps(response)
        app.logger.error(response_json)
        return Response(response_json, status=status, mimetype="application/json")


@app.route("/health", methods=["GET", "POST"])
def handle_health():
    # https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-probes/#define-a-liveness-http-request
    return "ready"


@app.route("/version")
def version():
    return f"v5.2019.05.25"


@app.route("/hello")
def hello_world():
    target = os.environ.get("TARGET", "World")
    return f"Hello2 {target}"


@app.route("/echo")
def handle_echo():
    """ Log message parameter to standard logging at given level. """
    level = int(request.args.get("level", 20))
    message = request.args.get("message", f"Hello from level {level}")
    logging.log(level, message)
    return json.dumps({"message": message, "level": level})


# when running in production, the docker image will contain a gunicorn
# server that will serve this flask application. during development we
# can also start the application directly for simplicity. do not run
# this development server in production.
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8081)))