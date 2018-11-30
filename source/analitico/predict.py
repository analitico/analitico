
import sys
import json
import datetime

import pandas as pd
import numpy as np

from catboost import Pool, CatBoostRegressor

from analitico.api import api_get_parameter, api_check_auth
from analitico.utilities import dataframe_to_catpool
from analitico.storage import storage_download_prj_settings, storage_download_prj_model

# internal caching
_models = {}
_settings = {}


def request_to_predictions(request, debug, project_id, version):
    """ Runs a model, returns predictions """
    api_check_auth(request, 'predict/' + project_id)

    results = { "meta": {} }
    preparing_on = datetime.datetime.now()

    # request can be for a single prediction or an array of records to predict
    test_data = api_get_parameter(request, "data")
    if type(test_data) is dict: test_data = [test_data]
    
    if project_id in _settings:
        settings = _settings[project_id]
    else:
        settings = storage_download_prj_settings(project_id)
        _settings[project_id] = settings

    # read features from configuration file
    features = settings['features']['all']
    categorical_features = settings['features']['categorical']
    timestamp_features = settings['features']['timestamp']

    # initialize data pool to be tested from json params
    test_df = pd.DataFrame(test_data)
    test_pool, _ = dataframe_to_catpool(test_df, features, categorical_features, timestamp_features)

    if debug:
        results["meta"]["preparation_ms"] = int((datetime.datetime.now() - preparing_on).total_seconds() * 1000)
        predicting_on = datetime.datetime.now()

    if project_id in _models:
        # predict using previously saved model
        model = _models[project_id]
    else:
        # create model object from stored model file
        model_filename = storage_download_prj_model(project_id)
        model = CatBoostRegressor()
        model.load_model(model_filename)
        _models[project_id] = model

    test_preds = model.predict(test_pool)
    test_preds = np.around(test_preds, decimals=3)

    results["data"] = {
        "predictions": list(test_preds)
    }

    if debug:
        results["meta"]["project_id"] = project_id
        results["meta"]["prediction_ms"] = int((datetime.datetime.now() - predicting_on).total_seconds() * 1000)
        results["meta"]["settings"] = settings

    return results
