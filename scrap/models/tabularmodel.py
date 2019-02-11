# Implements base class for tabular regressor and
# classification models using CatBoost as an engine
#
# Copyright (C) 2018 by Analitico.ai
# All rights reserved

import os
import os.path
import pandas as pd
import numpy as np
import tempfile
import multiprocessing
import catboost

import analitico.storage

from joblib import Parallel, delayed
from sklearn.model_selection import train_test_split
from catboost import Pool, CatBoost

from analitico.models import AnaliticoModel
from analitico.utilities import augment_timestamp_column, dataframe_to_catpool, time_ms, save_json, logger

# number of records per chunk when we preprocess them in parallel
PARALLEL_PREPROCESS_CHUNK_SIZE = 5000


class TabularModel(AnaliticoModel):
    """ Base model for tabular data processing with CatBoost gradient boosting """

    def __init__(self, settings):
        super().__init__(settings)
        logger.info("TabularModel - project_id: %s", self.project_id)

    # True if model can be preprocessed in parallel using all cores
    parallel = True

    #
    # training
    #

    def get_features(self):
        """ Feature columns that should be considered for training """
        return self.get_attribute("features.all")

    features = property(get_features)

    def get_label(self):
        """ Label column """
        return self.get_attribute("features.label")

    label = property(get_label)

    def read_data(self, data_url):
        """ Reads data from remote url .csv file into a pandas dataframe """
        # TODO specify types from settings for loading
        # https://stackoverflow.com/questions/24251219/pandas-read-csv-low-memory-and-dtype-options
        logger.info("TabularModel.read_data - data_url: %s", data_url)
        datatypes = self.get_attribute("training_data.datatypes", None)
        data_filename = analitico.storage.download_file(data_url)  # cached
        df = pd.read_csv(data_filename, low_memory=(datatypes is None), dtype=datatypes)
        return df

    def preprocess_data(self, df, training=False, results=None):
        """ Preprocess data before it's used to train the model """
        logger.info("TabularModel.preprocess_data")
        features = self.get_attribute("features.all")
        categorical_features = self.get_attribute("features.categorical")
        timestamp_features = self.get_attribute("features.timestamp")
        label_feature = self.get_attribute("features.label")

        # do we have rows without labels? if so, remove and warn
        if training:
            rows = len(df)
            df = df.dropna(subset=[label_feature])
            if len(df) < rows:
                logger.warning(
                    "TabularModel.preprocess_data - training data has %s rows without %s label",
                    rows - len(df),
                    label_feature,
                )

        categorical_features = categorical_features.copy()

        # save labels column
        df_labels = df[label_feature] if label_feature in df.columns else None
        # reorder columns, drop unused
        df = df[features]

        for cat in categorical_features:
            df[cat] = df[cat].astype(str)
            df = df.fillna(value={cat: ""})

        # augment timestamps
        if timestamp_features is not None:
            for timestamp_feature in timestamp_features:
                df = augment_timestamp_column(df, timestamp_feature)
                df = df.drop(columns=timestamp_feature)
                categorical_features.append(timestamp_feature + "_year")
                categorical_features.append(timestamp_feature + "_month")
                categorical_features.append(timestamp_feature + "_day")
                categorical_features.append(timestamp_feature + "_hour")
                categorical_features.append(timestamp_feature + "_minute")
                categorical_features.append(timestamp_feature + "_weekday")
                categorical_features.append(timestamp_feature + "_yearday")
                categorical_features.append(timestamp_feature + "_holiday")

        if training and self.debug:
            path = os.path.expanduser("~/" + self.project_id + "-preprocessed.csv")
            logger.info("TabularModel.preprocess_data - writing %s", path)
            df.to_csv(path)

        # indexes of columns with categorical features
        categorical_idx = [df.columns.get_loc(c) for c in df.columns if c in categorical_features]
        return df, df_labels, categorical_idx

    def preprocess_data_parallel(self, df, training=False, results=None):
        """ Split preprocessing in chunks and perform using all cores """

        chunk_dfs = [
            df[i : i + PARALLEL_PREPROCESS_CHUNK_SIZE] for i in range(0, df.shape[0], PARALLEL_PREPROCESS_CHUNK_SIZE)
        ]

        results = Parallel(n_jobs=multiprocessing.cpu_count())(
            delayed(self.preprocess_data)(chunk_df, training) for chunk_df in chunk_dfs
        )
        print("\n")

        augmented_data = []
        for result in results:
            for item in result:
                augmented_data.append(item)

    def create_model(self):
        """ Creates actual CatBoostClassifier or CatBoostRegressor model in subclass """
        raise NotImplementedError()

    def score_training(self, model: CatBoost, test_df, test_pool, test_labels, test_filename, results):
        """ Scores the results of this training for the CatBoostClassifier model """

        params = results["data"]["parameters"] = {}
        for key, value in model.get_params().items():
            params[key] = value
        params["best_iteration"] = model.get_best_iteration()
        params["best_score"] = model.get_best_score()

        # catboost can tell which features weigh more heavily on the predictions
        logger.info("TabularModel.score_training - features importance:")
        features_importance = results["data"]["features_importance"] = {}
        for label, importance in model.get_feature_importance(prettified=True):
            features_importance[label] = round(importance, 5)
            logger.info("%24s: %8.4f", label, importance)

        # make the prediction using the resulting model
        # output test set with predictions
        # after moving label to the end for easier reading
        test_predictions = model.predict(test_pool)
        label_feature = self.get_label()
        test_df = test_df.copy()
        test_df[label_feature] = test_labels
        cols = list(test_df.columns.values)
        cols.pop(cols.index(label_feature))
        test_df = test_df[cols + [label_feature]]
        test_df["prediction"] = test_predictions
        test_df.to_csv(test_filename)

    def train(self, training_id) -> dict:
        """ Trains model with given data (or data configured in settins) and returns training results """
        training_dir = os.path.join(tempfile.gettempdir(), training_id)
        if not os.path.isdir(training_dir):
            os.mkdir(training_dir)
        logger.info("TabularModel.train - training_id: %s, training_dir: %s", training_id, training_dir)

        try:
            started_on = time_ms()
            results = {"data": {}, "meta": {}}
            data = results["data"]
            meta = results["meta"]

            data["project_id"] = self.project_id
            data["training_id"] = training_id

            # load csv data from results of query joining multiple tables in source database
            loading_on = time_ms()
            data_url = self.get_attribute("training_data.url")
            df = self.read_data(data_url)
            meta["loading_ms"] = time_ms(loading_on)
            records = data["records"] = {}
            records["source"] = len(df)
            logger.info("TabularModel.train - loaded %d rows in %d ms", records["source"], meta["loading_ms"])

            if self.debug:
                # save a sample of the data as it was received for training
                sample_df = df.tail(5000)
                sample_df_filename = os.path.join(training_dir, self.project_id + "-sample.json")
                sample_df.to_json(sample_df_filename, orient="records")
                logger.info("TabularModel.train - saved sample of input records to %s", sample_df_filename)

            # DEBUG ONLY: CUT NUMBER OF ROW TO SPEED UP
            tail = self.get_attribute("parameters.tail", None)
            if tail and (len(df) > tail):
                df = df.tail(tail).copy()
                logger.warning("TabularModel.train - debug enabled, shrinking to %d tail rows", len(df))

            # filter outliers, calculate dynamic fields, augment timestamps, etc
            # then reorder the dataframe and keep only the columns that really matter
            # and return the dataframe, column of labels and indexes of the categoricals
            preprocessing_on = time_ms()
            logger.info("TabularModel.train - preprocessing data...")
            df, df_labels, categorical_idx = self.preprocess_data(df, training=True, results=results)
            records["total"] = len(df)
            meta["processing_ms"] = time_ms(preprocessing_on)
            logger.info(
                "TabularModel.train - preprocessed to %d rows in %d ms", records["total"], meta["processing_ms"]
            )

            # decide how to create test set from settings variable
            chronological = self.get_attribute("chronological", False)
            test_size = self.get_attribute("parameters.test_size", 0.10)

            # https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

            if chronological:
                # test set if from the last rows (chronological order)
                logger.info("TabularModel.train - chronological test set split")
                test_rows = int(len(df) * test_size)
                test_df = df[-test_rows:]
                test_labels = df_labels[-test_rows:]
                train_df = df[:-test_rows]
                train_labels = df_labels[:-test_rows]
            else:
                # test set if from a random assortment of rows
                logger.info("TabularModel.train - random test set split")
                train_df, test_df, train_labels, test_labels = train_test_split(
                    df, df_labels, test_size=0.10, random_state=42
                )

            # separate rows between training and testing set
            records["training"] = len(train_df)
            records["test"] = len(test_df)

            train_pool = Pool(train_df, train_labels, cat_features=categorical_idx)
            test_pool = Pool(test_df, test_labels, cat_features=categorical_idx)

            # release
            df = None

            # train the model
            logger.info("TabularModel.train - training model...")
            training_on = time_ms()
            model = self.create_model()
            model.fit(train_pool, eval_set=test_pool)
            meta["training_ms"] = time_ms(training_on)

            # where training files should be saved
            model_filename = os.path.join(training_dir, "model.cbm")
            test_filename = os.path.join(training_dir, "test.csv")
            results_filename = os.path.join(training_dir, "results.json")

            assets = data["assets"] = {}
            assets["model_path"] = model_filename
            assets["test_path"] = test_filename
            assets["training_path"] = results_filename

            # score test set, add related metrics to results
            self.score_training(model, test_df, test_pool, test_labels, test_filename, results)

            model.save_model(model_filename)
            meta["total_ms"] = time_ms(started_on)
            save_json(results, results_filename, indent=4)

            if self.upload:
                # upload model, results, predictions
                blobprefix = "training/" + training_id + "/"
                logger.info("TabularModel.train - uploading assets to %s", blobprefix)
                assets["model_url"] = analitico.storage.upload_file(blobprefix + "model.cbm", model_filename)
                assets["model_size"] = os.path.getsize(model_filename)
                assets["test_url"] = analitico.storage.upload_file(blobprefix + "test.csv", test_filename)
                assets["test_size"] = os.path.getsize(test_filename)
                # update with assets urls saving to storage
                assets["training_url"] = assets["model_url"].replace("model.cbm", "training.json")
                meta["total_ms"] = time_ms(started_on)  # include uploads
                save_json(results, results_filename, indent=4)
                assets["training_url"] = analitico.storage.upload_file(blobprefix + "training.json", results_filename)
                logger.info("TabularModel.train - uploaded assets")

            self.training = results
            return results

        except Exception as exc:
            logger.error(exc)
            raise

    #
    # inference
    #

    def predict(self, data):
        """ Predicts results for given data (implemented in subclass) """
        raise NotImplementedError()
