
import pandas as pd
import numpy as np

# predict
calls = 0


def handle2(event, context):
    response = {
        "statusCode": 200,
        "body": event
    }
    return response


# predict
def handle(event, **kwargs):
    global calls
    calls += 1
    event["calls"] = calls # add number of calls
    
    response = {
        "statusCode": 200,
        "body": event,
        "zio": "billy"
    }
    return response