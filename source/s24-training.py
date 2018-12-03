import json

import s24.ordersorting
import s24.ordertime

import api.models.machinelearning

if True:
    try:
        


        model = s24.ordertime.OrderTimeModel()
        scores = model.train()
        print(json.dumps(scores, indent=4))
    except Exception as exc:
        print(exc)


if False:

    try:
        # train order sorting model
        data, meta = s24.ordersorting.train()
        print(json.dumps(data, indent=4))
        print(json.dumps(meta, indent=4))
    except Exception as exc:
        print(exc)
