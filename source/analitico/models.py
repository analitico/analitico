
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

from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, median_absolute_error
from catboost import Pool, CatBoostRegressor, CatBoostClassifier
from pandas.api.types import CategoricalDtype
from pathlib import Path

from analitico.utilities import augment_timestamp_column, dataframe_to_catpool, time_ms, save_json
from analitico.storage import storage_download_prj_settings, storage_upload_prj_file, storage_cache
from rest_framework.exceptions import ParseError

##
## AnaliticoModel
##

class AnaliticoModel:

    # More info when in debugging mode
    debug:bool = False

    # project id used for tracking, directories, access, billing
    project_id:str = ''

    # directory where models are saved
    models_dir:str = ''

    def __init__(self):
        print('AnaliticoModel')

    def train(self) -> dict:
        return { 'data': None, 'meta': None }

    def predict(self, data) -> dict:
        """ Runs prediction on given data, returns predictions and metadata """
        return { 'data': None, 'meta': None }

##
## AnaliticoTabularRegressorModel
##

class AnaliticoTabularRegressorModel(AnaliticoModel):

    # Project settings    
    settings: dict = None

    # Model used for predictions
    model: CatBoostRegressor = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print('AnaliticoTabularRegressorModel')

    def _train_catboost_regressor(self, settings, train_df, test_df, results):
        # read features from configuration file
        features = settings['features']['all']
        categorical_features = settings['features']['categorical']
        timestamp_features = settings['features']['timestamp']
        label_feature = settings['features']['label']

        meta = results['meta']

        # initialize data pools
        preprocessing_on = time_ms()
        print('processing training data...')
        train_pool, _ = dataframe_to_catpool(train_df, features, categorical_features, timestamp_features, label_feature)
        print('processing test data...')
        test_pool, test_labels = dataframe_to_catpool(test_df, features, categorical_features, timestamp_features, label_feature)
        meta['processing_ms'] = time_ms(preprocessing_on)
        print('processed %d ms' % meta['processing_ms'])

        total_iterations = 50
        learning_rate = 1

        # create model with training parameters 
        model = CatBoostRegressor(iterations=total_iterations, learning_rate=learning_rate, depth=8, loss_function='RMSE')

        # train the model
        print('training...')
        training_on = time_ms()
        model.fit(train_pool, eval_set=test_pool)
        meta['total_iterations'] = total_iterations
        meta['best_iteration'] = model.get_best_iteration()
        meta['learning_rate'] = learning_rate
        meta['training_ms'] = time_ms(training_on)
        print('trained %d ms' % meta['training_ms'])

        # make the prediction using the resulting model
        test_predictions = model.predict(test_pool)

        # loss metrics on test set
        scores = results['data']['scores'] = {}
        scores['median_abs_error'] = round(median_absolute_error(test_predictions, test_labels), 5)
        scores['mean_abs_error'] = round(mean_absolute_error(test_predictions, test_labels), 5)
        scores['sqrt_mean_squared_error'] = round(np.sqrt(mean_squared_error(test_predictions, test_labels)), 5)
        return model, test_labels, test_predictions


    def _OFFtrain_catboost_multiclass(self, settings, train_df, test_df, results):
        # read features from configuration file
        features = settings['features']['all']
        categorical_features = settings['features']['categorical']
        timestamp_features = settings['features']['timestamp']
        label_feature = settings['features']['label']

        meta = results['meta']

        # initialize data pools
        preprocessing_on = time_ms()
        print('processing training data...')
        train_pool, _ = dataframe_to_catpool(train_df, features, categorical_features, timestamp_features, label_feature)
        print('processing test data...')
        test_pool, test_labels = dataframe_to_catpool(test_df, features, categorical_features, timestamp_features, label_feature)
        meta['processing_ms'] = time_ms(preprocessing_on)
        print('processed %d ms' % meta['processing_ms'])

        total_iterations = 50
        learning_rate = 1

        # create model with training parameters 
        model = CatBoostClassifier(iterations=total_iterations, learning_rate=learning_rate, depth=8, loss_function='MultiClass')

        # train the model
        print('training...')
        training_on = time_ms()
        model.fit(train_pool, eval_set=test_pool)
        meta['total_iterations'] = total_iterations
        meta['best_iteration'] = model.get_best_iteration()
        meta['learning_rate'] = learning_rate
        meta['training_ms'] = time_ms(training_on)
        print('trained %d ms' % meta['training_ms'])

        # make the prediction using the resulting model
        test_predictions = model.predict(test_pool)

        # loss metrics on test set
        scores = results['data']['scores'] = {}
        scores['median_abs_error'] = round(median_absolute_error(test_predictions, test_labels), 5)
        scores['mean_abs_error'] = round(mean_absolute_error(test_predictions, test_labels), 5)
        scores['sqrt_mean_squared_error'] = round(np.sqrt(mean_squared_error(test_predictions, test_labels)), 5)

        return model, test_labels, test_predictions    
        #model = CatBoostClassifier(iterations=total_iterations, learning_rate=learning_rate, depth=8, loss_function='MultiClass')


    def _train(self, data_url, upload=True):

        started_on = time_ms()
        results = { 'data': {}, 'meta': {} }
        data = results['data']
        meta = results['meta']
        data['project_id'] = self.project_id

        # read features from configuration file
        print('loading settings...')
        loading_on = time_ms()
        settings = storage_download_prj_settings(self.project_id)

        # load data from results of mysql query joining multiple tables in s24 database
        print('loading data...')    
        df = pd.read_csv(data_url, low_memory=False)
        meta['loading_ms'] = time_ms(loading_on)
        print('loaded %d ms' % meta['loading_ms'])
        
        records = data['records'] = {}
        records['source'] = len(df)

        # DEBUG ONLY TO LIMIT ROWS
        # df = df.head(10000)

        # remove outliers from s24 dataset
        # TODO: this should be done prior to submitting dataset
        if self.project_id[:9] == 's24-order':
            df = df[(df['total_min'] is not None) and (df['total_min'] < 120)]
            # sort orders oldest to most recent
            df = df.sort_values(by=['order_deliver_at_start'], ascending=True)

        # remove rows without labels
        label_feature = settings['features']['label']
        df = df.dropna(subset=[label_feature])
        records['filtered'] = len(df)

        # TODO: decide this from settings variable
        test_random = False
        test_size = 0.10

        if test_random:
            # test set if from a random assortment of rows
            train_df, test_df = train_test_split(df, test_size=0.05, random_state=42)
        else:
            # test set if from the last rows (chronological order)
            test_rows = int(len(df) * test_size)
            test_df = df[-test_rows:]
            train_df = df[:-test_rows]

        # separate rows between training and testing set
        records['training'] = len(train_df)
        records['test'] = len(test_df)

        # create model with training parameters 
        algorithm = settings['algorithm'] 
        if algorithm == 'catboost-regressor':
            model, test_labels, test_predictions = self._train_catboost_regressor(settings, train_df, test_df, results)
        # elif algorithm == 'catboost-multiclass':
        #     model, test_labels, test_predictions = _train_catboost_multiclass(settings, train_df, test_df, results)
        else:
            raise ParseError('Unknown algorithm: ' + algorithm) # bad request

        # catboost can tell which features weigh more heavily on the predictions
        feature_importance = model.get_feature_importance(prettified=True)
        data['features_importance'] = {}
        for label, importance in feature_importance:
            data['features_importance'][label] = round(importance, 5)

        # output test set with predictions
        test_df = test_df.copy()
        test_df[label_feature] = test_labels
        # move label to the end for easier reading
        cols = list(test_df.columns.values)
        cols.pop(cols.index(label_feature))
        test_df = test_df[cols+[label_feature]]
        test_df['prediction'] = test_predictions

        model_fname = os.path.join(self.models_dir, 'model.cbm')
        test_fname = os.path.join(self.models_dir, 'test.csv')
        results_fname = os.path.join(self.models_dir, 'scores.json')

        assets = data['assets'] = {}
        assets['model_path'] = model_fname
        assets['test_path'] = test_fname
        assets['scores_path'] = results_fname

        model.save_model(model_fname)
        test_df.to_csv(test_fname)

        meta['total_ms'] = time_ms(started_on)
        save_json(results, results_fname, indent=4)

        if upload:
            # save model, results, predictions
            blobprefix = 'training/' + started_on.strftime('%Y%m%dT%H%M%S') + '/'
            assets['model_url'] = storage_upload_prj_file(self.project_id, blobprefix + 'model.cbm', model_fname)
            assets['test_url'] = storage_upload_prj_file(self.project_id, blobprefix + 'test.csv', test_fname)

            # final update to results timestamps before saving the file to storage
            assets['scores_url'] = assets['model_url'].replace('model.cbm', 'scores.json')
            assets['scores_url'] = storage_upload_prj_file(self.project_id, blobprefix + 'scores.json', results_fname)

        return results

    def predict(self, data):
        """ Runs a model, returns predictions """

        results = { "meta": {} }
        results["meta"]["project_id"] = self.project_id
        if self.debug:
            results["meta"]["settings"] = self.settings

        # request can be for a single prediction or an array of records to predict
        if type(data) is dict: data = [data]
        
        if (self.settings is None):
            self.settings = storage_download_prj_settings(self.project_id)

        # read features from configuration file
        features = self.settings['features']['all']
        categorical_features = self.settings['features']['categorical']
        timestamp_features = self.settings['features']['timestamp']

        # initialize data pool to be tested from json params
        df = pd.DataFrame(data)
        pool, _ = dataframe_to_catpool(df, features, categorical_features, timestamp_features)

        # create model object from stored model file if not cached
        if self.model is None:
            loading_on = time_ms()
            model_path = os.path.join(self.models_dir, 'model.cbm')
            model_filename = storage_cache(model_path)
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
