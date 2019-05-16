
import os
import json 

from flask import Flask
from flask import request

app = Flask(__name__)

import notebook

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

@app.route('/hello')
def hello_world():
    target = os.environ.get('TARGET', 'World')
    return f'Hello {target}'


if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8081)))
