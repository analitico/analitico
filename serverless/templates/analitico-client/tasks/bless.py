##
## Code cell to append to the notebook that runs in a Job 
## in order to call the custom bless() method.
## 
## Parameters in the function are replaced by the real values.
##

import datetime
import analitico

blessed = False

try:
    blessed = bless(model_id=None, metrics={current_metrics}, blessed_model_id="{blessed_model_id}", blessed_metrics={blessed_metrics})
    print("using custom bless function defined for the recipe")
    
    print("model is blessed: " + str(blessed))
    if blessed:
        analitico.set_metric("blessed_on", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
except NameError:
    print("custom bless function not implemented")
except Exception as exc:
    print("custom bless function raised an error: %s".format(exc))
