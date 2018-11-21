
# Given an order, order details, customer and store
# information the regressor estimates how long it will
# take in minutes to pick the given shopping list at
# the store and deliver it to the customer's home
# Copyright (C) 2018 by Analitico.ai. All rights reserved. 

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

from analitico.api import api_get_parameter, ApiException
from analitico.utilities import augment_timestamp_column, dataframe_to_catpool, time_ms
from analitico.storage import storage_download_prj_settings, storage_upload_prj_file


def _train_catboost_regressor(settings, train_df, test_df, results):
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



def _train_catboost_multiclass(settings, train_df, test_df, results):
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



def train(project_id, data_url, upload=True):

    started_on = time_ms()
    results = { 'data': {}, 'meta': {} }
    data = results['data']
    meta = results['meta']
    data['project_id'] = project_id

    print('loading settings...')
    loading_on = time_ms()
    settings = storage_download_prj_settings(project_id)

    # read features from configuration file
    features = settings['features']['all']
    categorical_features = settings['features']['categorical']
    timestamp_features = settings['features']['timestamp']
    label_feature = settings['features']['label']

    # load data from results of mysql query joining multiple tables in s24 database
    print('loading data...')    
    df = pd.read_csv(data_url, low_memory=False)
    meta['loading_ms'] = time_ms(loading_on)
    print('loaded %d ms' % meta['loading_ms'])
    
    records = data['records'] = {}
    records['total'] = len(df)

    #DEBUG ONLY TO LIMIT ROWS
    #df = df.head(10000)

    # remove outliers from s24 dataset
    # TODO: this should be done prior to submitting dataset
    if project_id[:9] == 's24-order':
        df = df[(df['total_min'] is not None) and (df['total_min'] < 120)]
        # sort orders oldest to most recent
        df = df.sort_values(by=['order_deliver_at_start'], ascending=True)

    # remove rows without labels
    df = df.dropna(subset=[label_feature])
    records['valid'] = len(df)

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
        model, test_labels, test_predictions = _train_catboost_regressor(settings, train_df, test_df, results)
    elif algorithm == 'catboost-multiclass':
        model, test_labels, test_predictions = _train_catboost_multiclass(settings, train_df, test_df, results)
    else:
        raise ApiException('Unknown algorithm: ' + algorithm, status_code=400) # bad request

    # catboost can tell which features weigh more heavily on the predictions
    feature_importance = model.get_feature_importance(prettified=True)
    data['features_importance'] = {}
    for label, importance in feature_importance:
        data['features_importance'][label] = round(importance, 5)

    # save model, results, predictions
    saving_on = time_ms()
    blobprefix = 'training/' + started_on.strftime('%Y%m%dT%H%M%S') + '/'

    # output test set with predictions
    test_df = test_df.copy()
    test_df[label_feature] = test_labels
    
    # move label to the end for easier reading
    cols = list(test_df.columns.values)
    cols.pop(cols.index(label_feature))
    test_df = test_df[cols+[label_feature]]
    test_df['prediction'] = test_predictions

    if upload:
        _, test_fname = tempfile.mkstemp(suffix='.csv', text=True)
        _, model_fname = tempfile.mkstemp(suffix='.cbm', text=True)
        _, results_fname = tempfile.mkstemp(suffix='.json', text=True)

        test_df.to_csv(test_fname)
        model.save_model(model_fname)

        assets = data['assets'] = {}
        assets['test_url'] = storage_upload_prj_file(project_id, blobprefix + 'test.csv', test_fname)
        assets['model_url'] = storage_upload_prj_file(project_id, blobprefix + 'model.cbm', model_fname)

        # final update to results timestamps before saving the file to storage
        meta['saving_ms'] = time_ms(saving_on) # close enough
        meta['total_ms'] = time_ms(started_on) # close enough
        assets['results_url'] = assets['model_url'].replace('model.cbm', 'results.json')
        with open(results_fname, 'w') as results_file:
            json.dump(results, results_file, indent=4)
        assets['results_url'] = storage_upload_prj_file(project_id, blobprefix + 'results.json', results_fname)

        os.remove(test_fname)
        os.remove(model_fname)
        os.remove(results_fname)

    meta['saving_ms'] = time_ms(saving_on) # real
    meta['total_ms'] = time_ms(started_on) # real

    return results


def request_to_training(request, debug, project_id, version):
    """ Trains a model, returns results of training """
    data_url = api_get_parameter(request, "data_url")
    return train(project_id, data_url)
