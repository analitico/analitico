
import os
import json 
import logging
import notebook

from flask import Flask
from flask import request

logger = logging.getLogger("analitico")
logger.info("Starting")

app = Flask(__name__)

@app.route('/', methods = ['GET', 'POST'])
def handle_main():
    try:
        event = {}
        if request.is_json:
            event = request.get_json()
        response = notebook.handle(event=event, context=request)
    except Exception as exc:
        response = {
            "body": str(exc)
        }

    return json.dumps(response["body"])

@app.route('/health')
def handle_health():
    # https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-probes/#define-a-liveness-http-request
    return 'ready'

@app.route('/hello')
def hello_world():
    target = os.environ.get('TARGET', 'World')
    return f'Hello {target}'

@app.route('/echo')
def handle_echo():
    message = request.args.get('message', "Hello")
    level = int(request.args.get('level', 20))
    logger.log(level, message)
    return json.dumps({ "message": message, "level": level })



if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8081)))
