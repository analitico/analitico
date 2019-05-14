
import os
import json 

from flask import Flask
from flask import request

app = Flask(__name__)

import notebook



@app.route('/handle', methods = ['POST'])
def handle_post():
    print (request.is_json)
    event = request.get_json()
    response = notebook.handle(event=event, context=request)
    return json.dumps(response["body"])

@app.route('/')
def hello_world():
    target = os.environ.get('TARGET', 'World')

    #with open("data.csv") as f:
    #    line = f.readline()
    #    f.close()
    line = "ciao "

    return line + ' Hello v3 {}!\n'.format(target)

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8081)))
