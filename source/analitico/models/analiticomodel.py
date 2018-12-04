
# Implements machine learning classes for
# regression and classification problems.
# Handles storage of settings, configurations,
# training batches, predictions, APIs, etc.
#
# Copyright (C) 2018 by Analitico.ai
# All rights reserved

import os
import os.path
import time
import json
import datetime
import pandas as pd
import numpy as np
import tempfile
import copy

import analitico.storage

from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, median_absolute_error
from catboost import Pool, CatBoostRegressor, CatBoostClassifier
from pandas.api.types import CategoricalDtype
from pathlib import Path

from analitico.utilities import augment_timestamp_column, dataframe_to_catpool, time_ms, save_json, logger, get_dict_dot
from rest_framework.exceptions import ParseError

# subset of rows used for quick training while developing
_training_sample = None # eg: 5000 for quick run, None for all


##
## AnaliticoModel
##

class AnaliticoModel:

    # Project settings    
    settings: dict = None

    # training information (as returned by previous call to train)
    training:dict = None

    # project id used for tracking, directories, access, billing
    project_id:str = None

    # true if we're debugging (add extra info, etc)
    debug:bool = True

    def __init__(self, settings:dict):
        self.settings = settings
        self.project_id = settings.get('project_id')

    def train(self, training_id, upload=True) -> dict:
        """ Trains machine learning model and returns a dictionary with the training's results """
        raise NotImplementedError()

    def predict(self, data) -> dict:
        """ Runs prediction on given data, returns predictions and metadata """
        raise NotImplementedError()
