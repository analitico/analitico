
# Given an order, order details, customer and store
# information the regressor estimates how long it will
# take in minutes to pick the given shopping list at
# the store and deliver it to the customer's home

# Copyright (C) 2018 by Analitico.ai
# All rights reserved. 

import os
import os.path
import time
import json
import datetime
import pandas as pd
import numpy as np
import tempfile

from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, median_absolute_error
from catboost import Pool, CatBoostRegressor
from pandas.api.types import CategoricalDtype
from pathlib import Path

from analitico.api import api_get_parameter
from analitico.utilities import augment_timestamp_column, dataframe_to_catpool
from analitico.storage import storage_download_prj_settings, storage_upload_prj_file
from analitico.train import train


try:

    data_url = Path(os.getcwd(), '../data/s24/orders-joined.csv')
    data_exists = os.path.isfile(data_url)

    #results1 = train('s24-order-category', data_url)
    #print(json.dumps(results1, indent=4))

    results2 = train('s24-order-time', data_url, upload=True)
    print(json.dumps(results2, indent=4))

    results3 = train('s24-order-time-with-courier', data_url, upload=True)
    print(json.dumps(results3, indent=4))

except Exception as exc:
    print(exc)

