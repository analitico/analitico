import os

print(os.getcwd())
print(os.listdir())
print(os.listdir("analitico"))

import requests
import sys

# sys.path.append('/home/gionata/github/analitico/source/')

import analitico
import pandas as pd

TOKEN = "tok_XXX"
ENDPOINT = "https://staging.analitico.ai/api/"

api = analitico.authorize(token=TOKEN, endpoint=ENDPOINT)

# json = requests.post(ENDPOINT + "datasets/ds_s24_courier/jobs/process").json()

ds = api.get_dataset("ds_s24_order_detail")
df = ds.get_dataframe()


print("done")
