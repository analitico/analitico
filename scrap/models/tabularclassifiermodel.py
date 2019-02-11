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
_training_sample = None  # eg: 5000 for quick run, None for all

from analitico.models.tabularmodel import TabularModel

##
## TabularClassifierModel
##


class TabularClassifierModel(TabularModel):
    def __init__(self, settings):
        super().__init__(settings)
        logger.info("TabularClassifierModel - project_id: %s" % self.project_id)

    def create_model(self):
        """ Creates a CatBoostClassifier configured as requested """
        logger.info("TabularClassifierMode.create_model - creating CatBoostClassifier")
        iterations = self.get_attribute("parameters.iterations", 50)
        learning_rate = self.get_attribute("parameters.learning_rate", 1)
        return CatBoostClassifier(
            iterations=iterations, learning_rate=learning_rate, loss_function="MultiClass"
        )  # ccould be Logloss for binary

    def preprocess_data(self, df, training=False, results=None):
        """ Called before data is augmented and used for training """
        if training:
            # when training, store categories in results, encode as numbers
            label = self.get_label()
            df[label] = df[label].astype("category")
            label_classes = list(df[label].cat.categories)
            results["data"]["classes"] = label_classes
            df[label] = df[label].cat.codes
        return super().preprocess_data(df, training, results)

    def score_training(self, model, test_df, test_pool, test_labels, test_filename, results):
        """ Scores the results of this training for the CatBoostClassifier model """
        # There are many metrics available:
        # https://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics
        scores = results["data"]["scores"] = {}

        train_classes = results["data"]["classes"]  # the classes (actual strings)
        train_classes_codes = list(range(0, len(train_classes)))  # the codes, eg: 0, 1, 2...

        test_true = list(test_labels)  # test true labels
        test_preds = model.predict(test_pool, prediction_type="Class")  # prediction for each test sample
        test_probs = model.predict_proba(test_pool, verbose=True)  # probability for each class for each sample

        # Log loss, aka logistic loss or cross-entropy loss.
        scores["log_loss"] = round(sklearn.metrics.log_loss(test_true, test_probs, labels=train_classes_codes), 5)

        # In multilabel classification, this function computes subset accuracy:
        # the set of labels predicted for a sample must exactly match the corresponding set of labels in y_true.
        scores["accuracy_score"] = round(sklearn.metrics.accuracy_score(test_true, test_preds), 5)

        # The precision is the ratio tp / (tp + fp) where tp is the number of true positives
        # and fp the number of false positives. The precision is intuitively the ability
        # of the classifier not to label as positive a sample that is negative.
        # The best value is 1 and the worst value is 0.
        scores["precision_score_micro"] = round(
            sklearn.metrics.precision_score(test_true, test_preds, average="micro"), 5
        )
        scores["precision_score_macro"] = round(
            sklearn.metrics.precision_score(test_true, test_preds, average="macro"), 5
        )
        scores["precision_score_weighted"] = round(
            sklearn.metrics.precision_score(test_true, test_preds, average="weighted"), 5
        )

        # The recall is the ratio tp / (tp + fn) where tp is the number of true positives
        # and fn the number of false negatives. The recall is intuitively the ability
        # of the classifier to find all the positive samples.
        scores["recall_score_micro"] = round(sklearn.metrics.recall_score(test_true, test_preds, average="micro"), 5)
        scores["recall_score_macro"] = round(sklearn.metrics.recall_score(test_true, test_preds, average="macro"), 5)
        scores["recall_score_weighted"] = round(
            sklearn.metrics.recall_score(test_true, test_preds, average="weighted"), 5
        )

        logger.info("TabularClassifier.score_training - log_loss: %f", scores["log_loss"])
        logger.info("TabularClassifier.score_training - accuracy_score: %f", scores["accuracy_score"])
        logger.info("TabularClassifier.score_training - precision_score_micro: %f", scores["precision_score_micro"])
        logger.info("TabularClassifier.score_training - precision_score_macro: %f", scores["precision_score_macro"])

        # Report precision and recall for each of the classes
        scores["classes_scores"] = {}
        count = collections.Counter(test_true)
        precision_scores = sklearn.metrics.precision_score(test_true, test_preds, average=None)
        recall_scores = sklearn.metrics.recall_score(test_true, test_preds, average=None)
        for idx, val in enumerate(train_classes):
            scores["classes_scores"][val] = {
                "count": count[idx],
                "precision": round(precision_scores[idx], 5),
                "recall": round(recall_scores[idx], 5),
            }
        # superclass will save test.csv
        super().score_training(model, test_df, test_pool, test_labels, test_filename, results)

    #
    # inference
    #

    def predict(self, data):
        """ Runs model, returns predictions """
        results = {"data": {}, "meta": {}}
        if type(data) is dict:
            data = [data]  # could be single prediction or array

        # initialize data pool to be tested
        y_df = pd.DataFrame(data)
        y_df, _, categorical_idx = self.preprocess_data(y_df)
        y_pool = Pool(y_df, cat_features=categorical_idx)

        # create model object from stored file
        loading_on = time_ms()
        model_url = get_dict_dot(self.training, "data.assets.model_url")
        model_filename = analitico.storage.download_file(model_url)
        model = self.create_model()
        model.load_model(model_filename)
        results["meta"]["loading_ms"] = time_ms(loading_on)

        # predict class and probabilities of each class
        y_predictions = model.predict(y_pool, prediction_type="Class")  # array di array of 1 element with class index
        y_probabilities = model.predict(y_pool, prediction_type="Probability")  # array of array of probabilities
        y_classes = self.training["data"]["classes"]  # list of possible classes

        # create predictions with assigned class and probabilities
        preds = results["data"]["predictions"] = []
        for i in range(0, len(data)):
            preds.append(
                {
                    "class": y_classes[int(y_predictions[i][0])],
                    "probability": {y_classes[j]: y_probabilities[i][j] for j in range(0, len(y_classes))},
                }
            )
        return results
