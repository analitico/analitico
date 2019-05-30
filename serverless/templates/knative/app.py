
import os
import json 
import logging

import notebook
import analitico.utilities
from analitico import AnaliticoException, logger

from flask import Flask
from flask import request, Response

app = Flask(__name__)
app.logger.info("Started")

@app.route('/', methods = ['GET', 'POST'])
def handle_main():
    status = 200
    mimetype = 'application/json'

    try:
        event = {}
        if request.is_json:
            event = request.get_json()
            app.logger.info(event)
        try:
            # method declared as handle(event, context)
            response = notebook.handle(event=event, context=request)
        except AttributeError:
            raise AnaliticoException("The notebook should declare a handle(event, context) method that handles serverless requests.", status_code=405)
        except TypeError:
            try:
                # method declared as handle(event)
                response = notebook.handle(event=event)
            except TypeError:
                raise AnaliticoException("The notebook should declare a handle(event, context) method that handles serverless requests.", status_code=405)

    except Exception as exception:
        response = { "error": analitico.utilities.exception_to_dict(exception) }
        status = int(response["error"].get("status", 500))
        response_json = json.dumps(response)
        app.logger.error(response_json)
        return Response(response_json, status=status, mimetype='application/json')

    return json.dumps(response["body"] if "body" in response else response)



@app.route('/health', methods = ['GET', 'POST'])
def handle_health():
    # https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-probes/#define-a-liveness-http-request
    return 'ready'

@app.route('/version')
def version():
    return f'v5.2019.05.25'

@app.route('/hello')
def hello_world():
    target = os.environ.get('TARGET', 'World')
    return f'Hello2 {target}'

@app.route('/echo')
def handle_echo():
    message = request.args.get('message', "Hello")
    level = int(request.args.get('level', 20))
    app.logger.log(level, message)
    return json.dumps({ "message": message, "level": level })


# when running in production, the docker image will contain a gunicorn
# server that will serve this flask application. during development we
# can also start the application directly for simplicity. do not run 
# this development server in production.
if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8081)))
