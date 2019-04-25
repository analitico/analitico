import os
import os.path
import requests

from analitico import AnaliticoSdk

import logging
logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

# change here to your directory:
S24_ASSETS_PATH = "~/data/s24/2019-01-26/{}.csv"
S24_API_TOKEN = "tok_s24_579E5hOWw7k8"
S24_ENDPOINT = "https://s24.analitico.ai/api/"

S24_TABLES = (
    "order_detail", # largest table

    "courier",
    "courier_historical",
    "courier_role",
    "courier_vehicle",
    "customer",
    "order",
    "order_flags",
    "order_historical",
    "order_timestamps",
    "store",
    "ztl",
)

for table in S24_TABLES:
    asset = AnaliticoSdk.upload_dataset_asset(
        "ds_s24_{}".format(table),                  # dataset_id, eg: ds_s24_orders
        table + ".csv",                             # asset_id, eg: orders.csv
        S24_ASSETS_PATH.format(table),              # asset_path, eg: ~/dump/orders.csv
        S24_API_TOKEN,                              # token
        S24_ENDPOINT                                # endpoint: for now only staging, not yet in production!
    )
