
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

    def __init__(self, settings:dict):
        self.settings = settings
        self.project_id = settings.get('project_id')

    def train(self, training_id, upload=True) -> dict:
        """ Trains machine learning model and returns a dictionary with the training's results """
        raise NotImplementedError()

    def predict(self, data) -> dict:
        """ Runs prediction on given data, returns predictions and metadata """
        raise NotImplementedError()

##
## TabularRegressorModel
##

class TabularRegressorModel(AnaliticoModel):

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
        logger.info('TabularRegressorModel: %s' % self.project_id)

    #
    # training
    #

    def _train_preprocess_records(self, df):
        """ This method is called after data is loaded but before it is augmented and used for training """
        return df


    def _train_catboost_regressor(self, train_df, test_df, results):
        # read features from configuration file
        features = get_dict_dot(self.settings, 'features.all')
        categorical_features = get_dict_dot(self.settings, 'features.categorical')
        timestamp_features = get_dict_dot(self.settings, 'features.timestamp')
        label_feature = get_dict_dot(self.settings, 'features.label')

        meta = results['meta']

        # initialize data pools
        preprocessing_on = time_ms()
        logger.info('processing training data...')
        train_pool, _ = dataframe_to_catpool(train_df, features, categorical_features, timestamp_features, label_feature)
        logger.info('processing test data...')
        test_pool, test_labels = dataframe_to_catpool(test_df, features, categorical_features, timestamp_features, label_feature)
        meta['processing_ms'] = time_ms(preprocessing_on)
        logger.info('processed %d ms' % meta['processing_ms'])

        total_iterations = get_dict_dot(self.settings, 'iterations', 50)
        learning_rate = get_dict_dot(self.settings, 'learning_rate', 1)

        # create model with training parameters 
        model = CatBoostRegressor(task_type='GPU', iterations=total_iterations, learning_rate=learning_rate, depth=8, loss_function='RMSE')

        # train the model
        logger.info('training...')
        training_on = time_ms()
        model.fit(train_pool, eval_set=test_pool)
        meta['total_iterations'] = total_iterations
        meta['best_iteration'] = model.get_best_iteration()
        meta['learning_rate'] = learning_rate
        meta['training_ms'] = time_ms(training_on)
        logger.info('trained %d ms' % meta['training_ms'])

        # make the prediction using the resulting model
        test_predictions = model.predict(test_pool)

        # loss metrics on test set
        scores = results['data']['scores'] = {}
        scores['median_abs_error'] = round(median_absolute_error(test_predictions, test_labels), 5)
        scores['mean_abs_error'] = round(mean_absolute_error(test_predictions, test_labels), 5)
        scores['sqrt_mean_squared_error'] = round(np.sqrt(mean_squared_error(test_predictions, test_labels)), 5)
        return model, test_labels, test_predictions


    def train(self, training_id, upload=True) -> dict:
        """ Trains model with given data (or data configured in settins) and returns training results """
        temp_dir = tempfile.TemporaryDirectory()
        try:
            started_on = time_ms()
            results = { 'data': {}, 'meta': {} }
            data = results['data']
            meta = results['meta']
            data['project_id'] = self.project_id
            data['training_id'] = training_id

            # load csv data from results of query joining multiple tables in source database
            logger.info('loading data...')    
            loading_on = time_ms()
            data_url = get_dict_dot(self.settings, 'training_data.url')
            data_filename = analitico.storage.download_file(data_url) # cached
            df = pd.read_csv(data_filename, low_memory=False)
            meta['loading_ms'] = time_ms(loading_on)
            logger.info('loaded %d ms' % meta['loading_ms'])
            
            records = data['records'] = {}
            records['source'] = len(df)

            # DEBUG ONLY
            if _training_sample:
                logger.warning('Cutting rows down to %s for quicker debugging, disable in production', _training_sample)
                df = df.head(_training_sample)

            # filter outliers, etc
            df = self._train_preprocess_records(df)

            # remove rows without labels
            label_feature = get_dict_dot(self.settings, 'features.label')
            df = df.dropna(subset=[label_feature])
            records['total'] = len(df)

            # TODO: decide this from settings variable
            chronological = get_dict_dot(self.settings, 'chronological', False)
            test_size = 0.10

            # https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

            if chronological:
                # test set if from the last rows (chronological order)
                logger.info('chronological test set')
                test_rows = int(len(df) * test_size)
                test_df = df[-test_rows:]
                train_df = df[:-test_rows]
            else:
                # test set if from a random assortment of rows
                logger.info('random test set')
                train_df, test_df = train_test_split(df, test_size=0.05, random_state=42)

            # separate rows between training and testing set
            records['training'] = len(train_df)
            records['test'] = len(test_df)

            # create model with training parameters 
            model, test_labels, test_predictions = self._train_catboost_regressor(train_df, test_df, results)

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

            model_fname = os.path.join(temp_dir.name, 'model.cbm')
            test_fname = os.path.join(temp_dir.name, 'test.csv')
            results_fname = os.path.join(temp_dir.name, 'results.json')

            assets = data['assets'] = {}
            assets['model_path'] = model_fname
            assets['test_path'] = test_fname
            assets['training_path'] = results_fname

            model.save_model(model_fname)
            test_df.to_csv(test_fname)

            meta['total_ms'] = time_ms(started_on)
            save_json(results, results_fname, indent=4)
            
            if upload:
                # upload model, results, predictions
                blobprefix = 'training/' + training_id + '/'
                assets['model_url'] = analitico.storage.upload_file(blobprefix + 'model.cbm', model_fname)
                assets['model_size'] = os.path.getsize(model_fname)
                assets['test_url'] = analitico.storage.upload_file(blobprefix + 'test.csv', test_fname)
                assets['test_size'] = os.path.getsize(test_fname)
                # update with assets urls saving to storage
                assets['training_url'] = assets['model_url'].replace('model.cbm', 'training.json')
                meta['total_ms'] = time_ms(started_on) # include uploads
                save_json(results, results_fname, indent=4)
                assets['training_url'] = analitico.storage.upload_file(blobprefix + 'training.json', results_fname)

            self.training = results
            return results

        except Exception as exc:
            logger.error(exc)
            temp_dir.cleanup()
            raise

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
