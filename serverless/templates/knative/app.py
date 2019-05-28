
import os
import json 
import logging



import notebook
import analitico.utilities

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
        response = notebook.handle(event=event, context=request)

    except Exception as exception:
        response = analitico.utilities.exception_to_dict(exception)
        response_json = json.dumps(response)
        app.logger.error(response_json)
        return Response(response_json, status=int(response.get("status", 500)), mimetype='application/json')

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
