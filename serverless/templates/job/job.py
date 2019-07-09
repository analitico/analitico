

import logging
import datetime
import os

from time import sleep

logging.getLogger().setLevel(logging.DEBUG)
logging.info("let's do nothing for a while...")

#logging.info("environment:")
#logging.info(os.environ)

for key, value in os.environ.items():
    if key.startswith("ANALITICO_"):
        logging.info(f"{key}: {value}")


for i in range(0, 120):
    msg = "doing nothing " + str(i) + " at utc " + datetime.datetime.utcnow().isoformat()
    logging.info(msg)
    sleep(0.5)

logging.info("complete a whole lot of nothing, bye")
