import json
import datetime

import pippo
#import analitico

def echo1(event, context):
    current_time = datetime.datetime.now().time()
    body = {
        "message": "Hello, the current time is " + str(current_time) + ", ciao " + pippo.PLUTO
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

    

def echo2(event, context):
    current_time = datetime.datetime.now().time()
    body = {
        "message": "Hello v3, the current time is " + str(current_time),
        "event": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response


 
def echo3(event, context):
    current_time = datetime.datetime.now().time()
    body = {
        "message": "Hello v3, the current time is " + str(current_time) + ", action: "#+ analitico.ACTION_PREDICT
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
