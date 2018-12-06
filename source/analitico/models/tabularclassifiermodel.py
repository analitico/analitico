
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

import collections, numpy

import analitico.storage

import sklearn.metrics

from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, median_absolute_error, log_loss, accuracy_score
from catboost import Pool, CatBoostRegressor, CatBoostClassifier
from pandas.api.types import CategoricalDtype
from pathlib import Path

from analitico.utilities import augment_timestamp_column, dataframe_to_catpool, time_ms, save_json, logger, get_dict_dot
from rest_framework.exceptions import ParseError

# subset of rows used for quick training while developing
_training_sample = None # eg: 5000 for quick run, None for all

from analitico.models.tabularmodel import TabularModel

##
## TabularClassifierModel
##

class TabularClassifierModel(TabularModel):

    def __init__(self, settings):
        super().__init__(settings)
        logger.info('TabularClassifierModel - project_id: %s' % self.project_id)


    def create_model(self, iterations, learning_rate):
        """ Creates a CatBoostClassifier configured as requested """
        logger.info('TabularClassifierMode.create_model - creating CatBoostClassifier with iterations: %d, learning_rate: %f', iterations, learning_rate)
#        return CatBoostClassifier(iterations=iterations, learning_rate=learning_rate, loss_function='Logloss')
        return CatBoostClassifier(iterations=iterations, learning_rate=learning_rate, loss_function='MultiClass')


    def preprocess_data(self, df, training=False, results=None):
        """ Called before data is augmented and used for training """
        # convert category labels to numbers
        label = self.get_label()
        if training:
            # when training, store categories in results, encode as numbers
            df[label] = df[label].astype('category')
            label_classes = list(df[label].cat.categories)
            results['data']['classes'] = label_classes
            df[label] = df[label].cat.codes
        else:
            # for inference, retrieve categories from training, encode as numbers
            label_classes = self.training['data']['classes']
            df[label] = df[label].astype('category', label_classes)
            df[label] = df[label].cat.codes
        # let superclass complete processing
        return super().preprocess_data(df, training, results)


    def score_training(self, model, test_df, test_pool, test_labels, test_filename, results):
        """ Scores the results of this training for the CatBoostClassifier model """
        # There are many metrics available:
        # https://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics
        scores = results['data']['scores'] = {}

        train_classes = results['data']['classes'] # the classes (actual strings)
        train_classes_codes = list(range(0,len(train_classes))) # the codes, eg: 0, 1, 2...

        test_true = list(test_labels) # test true labels
        test_preds = model.predict(test_pool, prediction_type='Class') # prediction for each test sample
        test_probs = model.predict_proba(test_pool, verbose=True) # probability for each class for each sample
        
        # Log loss, aka logistic loss or cross-entropy loss.
        scores['log_loss'] = round(sklearn.metrics.log_loss(test_true, test_probs, labels=train_classes_codes), 5)

        # In multilabel classification, this function computes subset accuracy: 
        # the set of labels predicted for a sample must exactly match the corresponding set of labels in y_true.
        scores['accuracy_score'] = round(sklearn.metrics.accuracy_score(test_true, test_preds), 5)

        # The precision is the ratio tp / (tp + fp) where tp is the number of true positives 
        # and fp the number of false positives. The precision is intuitively the ability 
        # of the classifier not to label as positive a sample that is negative.
        # The best value is 1 and the worst value is 0.
        scores['precision_score_micro'] = round(sklearn.metrics.precision_score(test_true, test_preds, average='micro'), 5)
        scores['precision_score_macro'] = round(sklearn.metrics.precision_score(test_true, test_preds, average='macro'), 5)
        scores['precision_score_weighted'] = round(sklearn.metrics.precision_score(test_true, test_preds, average='weighted'), 5)

        # The recall is the ratio tp / (tp + fn) where tp is the number of true positives 
        # and fn the number of false negatives. The recall is intuitively the ability 
        # of the classifier to find all the positive samples.
        scores['recall_score_micro'] = round(sklearn.metrics.recall_score(test_true, test_preds, average='micro'), 5)
        scores['recall_score_macro'] = round(sklearn.metrics.recall_score(test_true, test_preds, average='macro'), 5)
        scores['recall_score_weighted'] = round(sklearn.metrics.recall_score(test_true, test_preds, average='weighted'), 5)

        # Report precision and recall for each of the classes
        scores['classes'] = {}
        count = collections.Counter(test_true)
        precision_scores = sklearn.metrics.precision_score(test_true, test_preds, average=None)
        recall_scores = sklearn.metrics.recall_score(test_true, test_preds, average=None)
        for idx, val in enumerate(train_classes):
            scores['classes'][val] = {
                'count': count[idx],
                'precision': round(precision_scores[idx], 5),
                'recall': round(recall_scores[idx], 5)
            }

        # superclass will save test.csv
        super().score_training(model, test_df, test_pool, test_labels, test_filename, results)


    #
    # inference
    #


    def JUSTCODEscore_training(self, model, test_df, test_pool, test_labels, test_filename, results):
        """ Scores the results of this training for the CatBoostClassifier model """

        # Add scoring to the results of this training. There are many metrics available:
        # https://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics


        # make the prediction using the resulting model

        # array of arrays with probability of each class for each sample
        p1 = model.predict(test_pool, prediction_type='Probability') # array di array di probabilità numero strano        

        # array with array of 1 item with class index of each sample        
        p2 = model.predict(test_pool, prediction_type='Class') # array di array da 1 elemento
                
        # array of arrays with raw probability of each class for each sample
        # p3 = model.predict(test_pool, prediction_type='RawFormulaVal') # array di array di probabilità numero strano



        y_pred = list(model.predict(test_pool))


        # same as calling model.predict(..., prediction_type='Probability')
        # array of arrays with probability of each class for each sample
        y_probabilities = model.predict_proba(test_pool, verbose=True)
        
        X_categories = results['data']['label_categories']
        X_categories_codes = list(range(0,len(X_categories)))       

       # y_categories = list(test_labels.astype('category').cat.categories)
        y_true = list(test_labels)

        # loss metrics on test set
        scores = results['data']['scores'] = {}
        scores['accuracy_score'] = round(sklearn.metrics.accuracy_score(y_true, y_pred), 5)

        # calculate precision of score for each label class
        scores['precision_score_weighted'] = sklearn.metrics.precision_score(y_true, y_pred, average='weighted')
        scores['precision_score'] = []
        ps = sklearn.metrics.precision_score(y_true, y_pred, average=None)
        for idx, val in enumerate(X_categories):
            scores['precision_score'].append((val, ps[idx]))

        scores['log_loss'] = sklearn.metrics.log_loss(y_true, y_probabilities, labels=X_categories_codes)


        # superclass will save test.csv
        super().score_training(model, test_df, test_pool, test_labels, test_filename, results)







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
