
print("pippo")

import analitico
import pandas as pd
import numpy as np

# predict
calls = 0

# predict
def handle(event, context, **kwargs):
    global calls
    calls += 1
    event["calls"] = calls # add number of calls
    raise analitico.AnaliticoException("This is an analitico exception", status_code=400)
    response = {
        "statusCode": 200,
        "body": event,
        "zio": "billy"
    }
    return response