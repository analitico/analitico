import json

import s24.ordersorting

try:
    # train order sorting model
    data, meta = s24.ordersorting.train()
    print(json.dumps(data, indent=4))
    print(json.dumps(meta, indent=4))
except Exception as exc:
    print(exc)
