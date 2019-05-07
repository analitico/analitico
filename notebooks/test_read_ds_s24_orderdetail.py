# setup for training AND prediction
import analitico
import analitico.plugin
import s24.plugin

from analitico.pandas import *

import pandas as pd
import numpy as np

# pass api token to create factory
factory = analitico.authorize("tok_demo1_croJ7gVp4cW9")

def sample(df):
    return df.sample(n=4)

import datetime
print(datetime.datetime.now())



# import processed source order_detail
df_odt = factory.run_plugin(settings = {
    "name": "analitico.plugin.DatasetSourcePlugin",
    "dataset_id": "ds_s24_order_detail"
})  

df_odt
