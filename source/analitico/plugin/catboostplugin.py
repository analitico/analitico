# Regression and classification plugins based on CatBoost

import pandas as pd
import numpy as np
import os.path

import sklearn.metrics
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    median_absolute_error,
    accuracy_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix,
)

import catboost
from catboost import CatBoostClassifier, CatBoostRegressor

from analitico.utilities import time_ms

import analitico.pandas
import analitico.schema
from analitico.schema import generate_schema, ANALITICO_TYPE_CATEGORY, ANALITICO_TYPE_INTEGER, ANALITICO_TYPE_FLOAT
from .interfaces import (
    IAlgorithmPlugin,
    PluginError,
    plugin,
    ALGORITHM_TYPE_REGRESSION,
    ALGORITHM_TYPE_BINARY_CLASSICATION,
    ALGORITHM_TYPE_MULTICLASS_CLASSIFICATION,
)

##
## CatBoostPlugin
##


@plugin
class CatBoostPlugin(IAlgorithmPlugin):
    """ Base class for CatBoost regressor and classifier plugins """

    results = None

    class Meta(IAlgorithmPlugin.Meta):
        name = "analitico.plugin.CatBoostPlugin"
        algorithms = [
            ALGORITHM_TYPE_REGRESSION,
            ALGORITHM_TYPE_BINARY_CLASSICATION,
            ALGORITHM_TYPE_MULTICLASS_CLASSIFICATION,
        ]

    def create_model(self, results):
        """ Creates actual CatBoostClassifier or CatBoostRegressor model """
        iterations = self.get_attribute("parameters.iterations", 50)
        learning_rate = self.get_attribute("parameters.learning_rate", 1)
        depth = self.get_attribute("parameters.depth", 8)
        if results:
            results["parameters"]["iterations"] = iterations
            results["parameters"]["learning_rate"] = learning_rate
            results["parameters"]["depth"] = depth

        algo = results.get("algorithm", ALGORITHM_TYPE_REGRESSION)
        if algo == ALGORITHM_TYPE_REGRESSION:
            return CatBoostRegressor(iterations=iterations, learning_rate=learning_rate, depth=depth)
        elif algo == ALGORITHM_TYPE_BINARY_CLASSICATION:
            # task_type="GPU", # runtime will pick up the GPU even if we don't specify it here
            return CatBoostClassifier(
                iterations=iterations, learning_rate=learning_rate, depth=depth, loss_function="Logloss"
            )
        elif algo == ALGORITHM_TYPE_MULTICLASS_CLASSIFICATION:
            return CatBoostClassifier(
                iterations=iterations, learning_rate=learning_rate, depth=depth, loss_function="MultiClass"
            )
        else:
            raise PluginError("CatBoostPlugin.create_model - can't handle algorithm type: %s", results["algorithm"])

    def get_categorical_idx(self, df):
        """ Return indexes of the columns that should be considered categorical for the purpose of catboost training """
        categorical_idx = []
        for i, column in enumerate(df.columns):
            if analitico.schema.get_column_type(df, column) is analitico.schema.ANALITICO_TYPE_CATEGORY:
                categorical_idx.append(i)
                df[column].replace(np.nan, "", regex=True, inplace=True)
                self.factory.debug("%3d %s (%s/categorical)", i, column, df[column].dtype.name)
            else:
                self.factory.debug("%3d %s (%s)", i, column, df[column].dtype.name)
        return categorical_idx

    def validate_schema(self, train_df, test_df):
        """ Checks training and test dataframes to make sure they have matching schemas """
        train_schema = generate_schema(train_df)
        if test_df:
            test_schema = generate_schema(test_df)
            train_columns = train_schema["columns"]
            test_columns = test_schema["columns"]
            if len(train_columns) != len(test_columns):
                msg = "{} - training data has {} columns while test data has {} columns".format(
                    self.name, len(train_columns), len(test_columns)
                )
                raise PluginError(msg)
            for i in range(0, len(train_columns)):
                if train_columns[i]["name"] != test_columns[i]["name"]:
                    msg = "{} - column {} of train '{}' and test '{}' have different names".format(
                        self.name, i, train_columns[i]["name"], test_columns[i]["name"]
                    )
                    raise PluginError(msg)
                if train_columns[i]["type"] != test_columns[i]["type"]:
                    msg = "{} - column {} of train '{}' and test '{}' have different names".format(
                        self.name, i, train_columns[i]["type"], test_columns[i]["type"]
                    )
                    raise PluginError(msg)
        return train_schema

    def score_training(
        self,
        model: catboost.CatBoost,
        test_df: pd.DataFrame,
        test_pool: catboost.Pool,
        test_labels: pd.DataFrame,
        results: dict,
    ):
        """ Scores the results of this training """
        for key, value in model.get_params().items():
            results["parameters"][key] = value

        results["scores"]["best_iteration"] = model.get_best_iteration()

        best_score = model.get_best_score()
        try:
            best_score["training"] = best_score.pop("learn")
            best_score["validation"] = best_score.pop("validation_0")
        except KeyError:
            pass
        results["scores"]["best_score"] = best_score

        # result for each evaluation epoch
        evals_result = model.get_evals_result()
        try:
            evals_result["training"] = evals_result.pop("learn")
            evals_result["validation"] = evals_result.pop("validation_0")
        except KeyError:
            pass
        results["scores"]["iterations"] = evals_result

        # catboost can tell which features weigh more heavily on the predictions
        self.info("features importance:")
        features_importance = results["scores"]["features_importance"] = {}
        for label, importance in model.get_feature_importance(prettified=True):
            features_importance[label] = round(importance, 5)
            self.info("%24s: %8.4f", label, importance)

        # make the prediction using the resulting model
        # output test set with predictions
        # after moving label to the end for easier reading
        test_predictions = model.predict(test_pool)
        label = test_labels.name
        test_df[label] = test_labels
        cols = list(test_df.columns.values)
        cols.pop(cols.index(label))
        test_df = test_df[cols + [label]]
        test_df["prediction"] = test_predictions
        test_df = analitico.pandas.pd_sample(test_df, 200)  # just sampling
        artifacts_path = self.factory.get_artifacts_directory()
        test_df.to_csv(os.path.join(artifacts_path, "test.csv"))

    def score_regressor_training(self, model, test_df, test_pool, test_labels, results):
        test_preds = model.predict(test_pool)
        results["scores"]["median_abs_error"] = round(median_absolute_error(test_preds, test_labels), 5)
        results["scores"]["mean_abs_error"] = round(mean_absolute_error(test_preds, test_labels), 5)
        results["scores"]["sqrt_mean_squared_error"] = round(np.sqrt(mean_squared_error(test_preds, test_labels)), 5)

    def score_classifier_training(self, model, test_df, test_pool, test_labels, results):
        """ Scores the results of this training for the CatBoostClassifier model """
        # There are many metrics available:
        # https://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics

        scores = results["scores"]
        train_classes = results["data"]["classes"]  # the classes (actual strings)
        train_classes_codes = list(range(0, len(train_classes)))  # the codes, eg: 0, 1, 2...

        test_true = list(test_labels)  # test true labels
        test_preds = model.predict(test_pool, prediction_type="Class")  # prediction for each test sample
        test_probs = model.predict_proba(test_pool, verbose=True)  # probability for each class for each sample

        # Log loss, aka logistic loss or cross-entropy loss.
        scores["log_loss"] = round(sklearn.metrics.log_loss(test_true, test_probs, labels=train_classes_codes), 5)

        # In multilabel classification, this function computes subset accuracy:
        # the set of labels predicted for a sample must exactly match the corresponding set of labels in y_true.
        scores["accuracy_score"] = round(accuracy_score(test_true, test_preds), 5)

        # The precision is the ratio tp / (tp + fp) where tp is the number of true positives
        # and fp the number of false positives. The precision is intuitively the ability
        # of the classifier not to label as positive a sample that is negative.
        # The best value is 1 and the worst value is 0.
        scores["precision_score_micro"] = round(precision_score(test_true, test_preds, average="micro"), 5)
        scores["precision_score_macro"] = round(precision_score(test_true, test_preds, average="macro"), 5)
        scores["precision_score_weighted"] = round(precision_score(test_true, test_preds, average="weighted"), 5)

        # The recall is the ratio tp / (tp + fn) where tp is the number of true positives
        # and fn the number of false negatives. The recall is intuitively the ability
        # of the classifier to find all the positive samples.
        scores["recall_score_micro"] = round(recall_score(test_true, test_preds, average="micro"), 5)
        scores["recall_score_macro"] = round(recall_score(test_true, test_preds, average="macro"), 5)
        scores["recall_score_weighted"] = round(recall_score(test_true, test_preds, average="weighted"), 5)

        self.info("log_loss: %f", scores["log_loss"])
        self.info("accuracy_score: %f", scores["accuracy_score"])
        self.info("precision_score_micro: %f", scores["precision_score_micro"])
        self.info("precision_score_macro: %f", scores["precision_score_macro"])

        # complete classification report and confusion matrix
        # https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html#sklearn.metrics.classification_report
        # https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html#sklearn.metrics.confusion_matrix
        scores["classification_report"] = classification_report(
            test_true, test_preds, target_names=train_classes, output_dict=True
        )
        scores["confusion_matrix"] = confusion_matrix(test_true, test_preds).tolist()

    def train(self, train, test, results, *args, **kwargs):
        """ Train with algorithm and given data to produce a trained model """
        try:
            assert isinstance(train, pd.DataFrame) and len(train.columns) > 1
            train_df = train
            test_df = test

            # if not specified the prediction target will be the last column of the dataset
            label = self.get_attribute("data.label")
            if not label:
                label = train_df.columns[len(train_df.columns) - 1]
            results["data"]["label"] = label

            # choose between regression, binary classification and multiclass classification
            label_type = analitico.schema.get_column_type(train_df, label)
            self.info("label: %s", label)
            self.info("label_type: %s", label_type)
            if label_type == analitico.schema.ANALITICO_TYPE_CATEGORY:
                label_classes = list(train_df[label].cat.categories)
                results["data"]["classes"] = label_classes
                train_df[label] = train_df[label].cat.codes
                results["algorithm"] = (
                    ALGORITHM_TYPE_BINARY_CLASSICATION
                    if len(label_classes) == 2
                    else ALGORITHM_TYPE_MULTICLASS_CLASSIFICATION
                )
                self.info("classes: %s", label_classes)
            else:
                results["algorithm"] = ALGORITHM_TYPE_REGRESSION
            self.info("algorithm: %s", results["algorithm"])

            # remove rows with missing label from training and test sets
            train_rows = len(train_df)
            train_df = train_df.dropna(subset=[label])
            if len(train_df) < train_rows:
                self.warning("Training data has %s rows without '%s' label", train_rows - len(train_df), label)
            if test_df:
                test_rows = len(test_df)
                test_df = test_df.dropna(subset=[label])
                if len(test_df) < test_rows:
                    self.warning("Test data has %s rows without '%s' label", test_rows - len(test_df), label)

            # make sure schemas match
            train_schema = self.validate_schema(train_df, test_df)

            # shortened training was requested?
            tail = self.get_attribute("parameters.tail", 0)
            if tail > 0:
                self.info("Tail: %d, cutting training data", tail)
                train_df = train_df.tail(tail).copy()

            # create test set from training set if not provided
            if not test_df:
                # decide how to create test set from settings variable
                # https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
                chronological = self.get_attribute("data.chronological", False)
                test_size = self.get_attribute("parameters.test_size", 0.20)
                results["data"]["chronological"] = chronological
                results["parameters"]["test_size"] = test_size
                if chronological:
                    # test set if from the last rows (chronological order)
                    self.info("Test set split: chronological")
                    test_rows = int(len(train_df) * test_size)
                    test_df = train_df[-test_rows:]
                    train_df = train_df[:-test_rows]
                else:
                    # test set if from a random assortment of rows
                    self.info("Test set split: random")
                    train_df, test_df, = train_test_split(train_df, test_size=test_size, random_state=42)

            self.info("training: %d rows", len(train_df))
            self.info("testing: %d rows", len(test_df))

            # validate data types
            for column in train_schema["columns"]:
                if column["type"] not in ("integer", "float", "boolean", "category"):
                    self.warning(
                        "Column '%s' of type '%s' is incompatible and will be dropped", column["name"], column["type"]
                    )
                    train_df = train_df.drop(column["name"], axis=1)
                    test_df = test_df.drop(column["name"], axis=1)

            # save schema after dropping unused columns
            results["data"]["schema"] = generate_schema(train_df)
            results["data"]["source_records"] = len(train)
            results["data"]["training_records"] = len(train_df)
            results["data"]["test_records"] = len(test_df)
            results["data"]["dropped_records"] = len(train) - len(train_df) - len(test_df)

            # save some training data for debugging
            artifacts_path = self.factory.get_artifacts_directory()
            self.info("artifacts_path: %s", artifacts_path)

            samples_df = analitico.pandas.pd_sample(train_df, 200)
            samples_path = os.path.join(artifacts_path, "training-samples.json")
            samples_df.to_json(samples_path, orient="records")
            self.info("saved: %s (%d bytes)", samples_path, os.path.getsize(samples_path))
            samples_path = os.path.join(artifacts_path, "training-samples.csv")
            samples_df.to_csv(samples_path)
            self.info("saved: %s (%d bytes)", samples_path, os.path.getsize(samples_path))

            # split data and labels
            train_labels = train_df[label]
            train_df = train_df.drop([label], axis=1)
            test_labels = test_df[label]
            test_df = test_df.drop([label], axis=1)

            # indexes of columns that should be considered categorical
            categorical_idx = self.get_categorical_idx(train_df)
            train_pool = catboost.Pool(train_df, train_labels, cat_features=categorical_idx)
            test_pool = catboost.Pool(test_df, test_labels, cat_features=categorical_idx)

            # create regressor or classificator then train
            training_on = time_ms()
            model = self.create_model(results)
            model.fit(train_pool, eval_set=test_pool)
            results["performance"]["training_ms"] = time_ms(training_on)

            # score test set, add related metrics to results
            self.score_training(model, test_df, test_pool, test_labels, results)
            if results["algorithm"] == ALGORITHM_TYPE_REGRESSION:
                self.score_regressor_training(model, test_df, test_pool, test_labels, results)
            else:
                self.score_classifier_training(model, test_df, test_pool, test_labels, results)

            # save model file and training results
            model_path = os.path.join(artifacts_path, "model.cbm")
            model.save_model(model_path)
            results["scores"]["model_size"] = os.path.getsize(model_path)
            self.info("saved: %s (%d bytes)", model_path, os.path.getsize(model_path))
            return results

        except Exception as exc:
            self.exception("CatBoostPlugin - error while training: %s", str(exc), exception=exc)

    def predict(self, data, training, results, *args, **kwargs):
        """ Return predictions from trained model """

        # data should already come in as pd.DataFrame but it's just a dictionary we convert it
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame.from_dict(data, orient="columns")

        # record that we're predicting on after augmentation is added
        # to the results. if the endpoint or the jupyter notebook in
        # charge of communicating with the caller does not want to send
        # this information back, it can always take it out. in the future
        # we may want to optimized here and add this optionally instead.
        results["records"] = analitico.pandas.pd_to_dict(data)

        # initialize data pool to be tested
        categorical_idx = self.get_categorical_idx(data)
        data_pool = catboost.Pool(data, cat_features=categorical_idx)

        # create model object from stored file
        loading_on = time_ms()
        model_path = os.path.join(self.factory.get_artifacts_directory(), "model.cbm")
        if not os.path.isfile(model_path):
            self.exception("CatBoostPlugin.predict - cannot find saved model in %s", model_path)

        model = self.create_model(training)
        model.load_model(model_path)
        results["performance"]["loading_ms"] = time_ms(loading_on)

        algo = training.get("algorithm", ALGORITHM_TYPE_REGRESSION)
        if algo == ALGORITHM_TYPE_REGRESSION:
            y_predictions = model.predict(data_pool)
            y_predictions = np.around(y_predictions, decimals=3)
            results["predictions"] = list(y_predictions)

        else:
            # predict class and probabilities of each class
            y_predictions = model.predict(
                data_pool, prediction_type="Class"
            )  # array di array of 1 element with class index
            y_probabilities = model.predict(data_pool, prediction_type="Probability")  # array of array of probabilities
            y_classes = training["data"]["classes"]  # list of possible classes

            preds = results["predictions"] = []
            probs = results["probabilities"] = []

            # create predictions with assigned class and probabilities
            if algo == ALGORITHM_TYPE_MULTICLASS_CLASSIFICATION:
                for i in range(0, len(data)):
                    preds.append(y_classes[int(y_predictions[i][0])])
                    probs.append({y_classes[j]: y_probabilities[i][j] for j in range(0, len(y_classes))})

            elif algo == ALGORITHM_TYPE_BINARY_CLASSICATION:
                for i in range(0, len(data)):
                    preds.append(y_classes[int(y_predictions[i])])
                    probs.append({y_classes[0]: y_probabilities[i][0], y_classes[1]: y_probabilities[i][1]})

        return results


##
## CatBoostRegressorPlugin
##


@plugin
class CatBoostRegressorPlugin(CatBoostPlugin):
    """ A tabular data regressor based on CatBoost library """

    class Meta(CatBoostPlugin.Meta):
        name = "analitico.plugin.CatBoostRegressorPlugin"
        algorithms = [ALGORITHM_TYPE_REGRESSION]


##
## CatBoostClassifierPlugin
##


@plugin
class CatBoostClassifierPlugin(CatBoostPlugin):
    """ A tabular data classifier based on CatBoost """

    class Meta(CatBoostPlugin.Meta):
        name = "analitico.plugin.CatBoostClassifierPlugin"
        algorithms = [ALGORITHM_TYPE_BINARY_CLASSICATION, ALGORITHM_TYPE_MULTICLASS_CLASSIFICATION]
