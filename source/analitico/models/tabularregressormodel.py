
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

import analitico.models

from analitico.utilities import augment_timestamp_column, dataframe_to_catpool, time_ms, save_json, logger, get_dict_dot
from rest_framework.exceptions import ParseError

# subset of rows used for quick training while developing
_training_sample = None # eg: 5000 for quick run, None for all

from analitico.models import TabularModel

##
## TabularRegressorModel
##

class TabularRegressorModel(TabularModel):

    # feature columns that should be considered for training
    def get_features(self):
        return get_dict_dot(self.settings, 'features.all')
    features = property(get_features)

    # label column
    def get_label(self):
        return get_dict_dot(self.settings, 'features.label')
    label = property(get_label)

    # Model used for predictions
    model: CatBoostRegressor = None

    def __init__(self, settings):
        super().__init__(settings)
        logger.info('TabularRegressorModel - project_id: %s' % self.project_id)

    #
    # training
    #

    def create_model(self, iterations, learning_rate):
        """ Creates a CatBoostRegressor configured as requested """
        return CatBoostRegressor(iterations=iterations, learning_rate=learning_rate, depth=8, loss_function='Logloss')


    def preprocess_data(self, df, training=False):
        """ This method is called after data is loaded but before it is used for training """
        return super().preprocess_data(df, training)


    def score_training(self, model, test_df, test_pool, test_labels, test_filename, results):
        """ Scores the results of this training for the CatBoostClassifier model """
        # make the prediction using the resulting model
        test_predictions = model.predict(test_pool)

        # Get predicted probabilities for each class
        #test_probabilities = model.predict_proba(test_pool)
        # Get predicted RawFormulaVal
        #test_raw = model.predict(test_pool, prediction_type='RawFormulaVal')

        # loss metrics on test set
        scores = results['data']['scores'] = {}
        scores['median_abs_error'] = round(median_absolute_error(test_predictions, test_labels), 5)
        scores['mean_abs_error'] = round(mean_absolute_error(test_predictions, test_labels), 5)
        scores['sqrt_mean_squared_error'] = round(np.sqrt(mean_squared_error(test_predictions, test_labels)), 5)

        # output test set with predictions
        # after moving label to the end for easier reading
        label_feature = self.get_label()
        test_df = test_df.copy()
        test_df[label_feature] = test_labels
        cols = list(test_df.columns.values)
        cols.pop(cols.index(label_feature))
        test_df = test_df[cols+[label_feature]]
        test_df['prediction'] = test_predictions
        test_df.to_csv(test_filename)


    #
    # inference
    #

    def predict(self, data, debug=False):
        """ Runs a model, returns predictions """

        results = { "meta": {} }
        results["meta"]["project_id"] = self.project_id
        
        if debug:
            results["meta"]["settings"] = self.settings

        # request can be for a single prediction or an array of records to predict
        if type(data) is dict: data = [data]
        
        # read features from configuration file
        features = get_dict_dot(self.settings, 'features.all')
        categorical_features = get_dict_dot(self.settings, 'features.categorical')
        timestamp_features = get_dict_dot(self.settings, 'features.timestamp')

        # initialize data pool to be tested from json params
        df = pd.DataFrame(data)
        pool, _ = dataframe_to_catpool(df, features, categorical_features, timestamp_features)

        # create model object from stored model file if not cached
        if self.model is None:
            loading_on = time_ms()
            model_url = get_dict_dot(self.training, 'data.assets.model_url')
            model_filename = analitico.storage.download_file(model_url)
            model = CatBoostRegressor()
            model.load_model(model_filename)
            self.model = model
            results["meta"]["loading_ms"] = time_ms(loading_on)

        predictions = self.model.predict(pool)
        predictions = np.around(predictions, decimals=3)

        results["data"] = {
            "predictions": list(predictions)
        }
        return results
