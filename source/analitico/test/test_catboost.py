import unittest
import os
import os.path
import pytest
import pandas as pd

import sklearn.metrics
from sklearn.datasets import load_boston

from analitico.factory import Factory
from analitico.plugin import *
from .test_mixin import TestMixin

# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + "/assets"


@pytest.mark.django_db
class CatBoostTests(unittest.TestCase, TestMixin):
    """ Unit testing of machine learning algorithms """

    def train_iris(self, factory):
        """ Train iris.csv dataset using a multiclass classifier, return df and training results """
        csv_path = self.get_asset_path("iris_1.csv")
        df = pd.read_csv(csv_path)
        df = df.drop(columns=["Id"])
        df["Species"] = df["Species"].astype("category")
        catboost = CatBoostPlugin(factory=factory, parameters={"learning_rate": 0.2})
        # run training
        training = catboost.run(df.copy(), action="recipe/train")
        self.assertIsNotNone(training)
        return df, training

    def test_catboost_binary_classifier_training(self):
        """ Test training catboost as a binary classifier """
        try:
            with Factory() as factory:
                csv_path = self.get_asset_path("titanic_1.csv")
                recipe = RecipePipelinePlugin(
                    factory=factory,
                    plugins=[
                        CsvDataframeSourcePlugin(
                            source={"url": csv_path, "schema": {"apply": [{"name": "Survived", "type": "category"}]}}
                        ),
                        CatBoostPlugin(parameters={"learning_rate": 0.2}),
                    ],
                )

                self.assertEqual(len(recipe.plugins), 2)
                self.assertTrue(isinstance(recipe, RecipePipelinePlugin))
                self.assertTrue(isinstance(recipe.plugins[0], CsvDataframeSourcePlugin))
                self.assertTrue(isinstance(recipe.plugins[1], CatBoostPlugin))

                # run training
                results = recipe.run(action="recipe/train")

                self.assertIsNotNone(results)
                self.assertEqual(results["data"]["label"], "Survived")
                self.assertEqual(results["data"]["source_records"], 891)
                self.assertEqual(results["data"]["training_records"], 712)
                self.assertEqual(results["data"]["test_records"], 179)

                self.assertEqual(len(results["data"]["classes"]), 2)
                self.assertEqual(results["data"]["classes"][0], 0)
                self.assertEqual(results["data"]["classes"][1], 1)

                self.assertEqual(results["parameters"]["loss_function"], "Logloss")
                self.assertEqual(results["parameters"]["test_size"], 0.2)
                self.assertEqual(results["parameters"]["learning_rate"], 0.2)

                # model was saved?
                artifacts = factory.get_artifacts_directory()
                model_path = os.path.join(artifacts, "model.cbm")
                self.assertTrue(os.path.isfile(model_path))

        except Exception as exc:
            factory.error("test_catboost_binary_classifier - " + str(exc))
            pass

    def test_catboost_binary_classifier_prediction(self):
        """ Test predictions with catboost as a binary classifier """
        try:
            with Factory() as factory:
                csv_path = self.get_asset_path("titanic_1.csv")
                df = pd.read_csv(csv_path)
                df["Survived"] = df["Survived"].astype("category")
                catboost = CatBoostPlugin(factory=factory, parameters={"learning_rate": 0.2})

                # run training
                training = catboost.run(df.copy(), action="recipe/train")
                self.assertIsNotNone(training)

                df_labels = df[["Survived"]]
                df = df.drop(columns=["Survived"])
                predict = catboost.run(df, action="endpoint/predict")

                # check to make sure predictions are from available labels
                self.assertIn("predictions", predict)
                self.assertEqual(len(predict["predictions"]), len(df))
                for prediction in predict["predictions"]:
                    self.assertIn(prediction, training["data"]["classes"])

                # make sure each record had each class scored
                self.assertIn("probabilities", predict)
                self.assertEqual(len(predict["probabilities"]), len(df))
                for probability in predict["probabilities"]:
                    for label_class in training["data"]["classes"]:
                        self.assertIn(label_class, probability)

                # check correctness of predictions
                report = sklearn.metrics.classification_report(df_labels, predict["predictions"], output_dict=True)
                self.assertGreater(report["0"]["f1-score"], 0.80)
                self.assertGreater(report["1"]["f1-score"], 0.65)

        except Exception as exc:
            factory.error("test_catboost_multiclass_classifier_prediction - " + str(exc))
            raise exc

    def test_catboost_binary_classifier_prediction_with_labels(self):
        """ Test predictions with catboost as a binary classifier (using labels instead of int) """
        try:
            with Factory() as factory:
                csv_path = self.get_asset_path("titanic_1.csv")
                df = pd.read_csv(csv_path)
                df["Survived"] = df["Survived"].map({0: "No", 1: "Yes"})
                df["Survived"] = df["Survived"].astype("category")

                catboost = CatBoostPlugin(factory=factory, parameters={"learning_rate": 0.2})

                # run training
                training = catboost.run(df.copy(), action="recipe/train")
                self.assertIsNotNone(training)

                df_labels = df[["Survived"]]
                df = df.drop(columns=["Survived"])
                predict = catboost.run(df, action="endpoint/predict")

                # check to make sure predictions are from available labels
                self.assertIn("predictions", predict)
                self.assertEqual(len(predict["predictions"]), len(df))
                for prediction in predict["predictions"]:
                    self.assertIn(prediction, training["data"]["classes"])

                # make sure each record had each class scored
                self.assertIn("probabilities", predict)
                self.assertEqual(len(predict["probabilities"]), len(df))
                for probability in predict["probabilities"]:
                    for label_class in training["data"]["classes"]:
                        self.assertIn(label_class, probability)

                # check correctness of predictions
                report = sklearn.metrics.classification_report(df_labels, predict["predictions"], output_dict=True)
                self.assertGreater(report["No"]["f1-score"], 0.80)
                self.assertGreater(report["Yes"]["f1-score"], 0.65)

        except Exception as exc:
            factory.error("test_catboost_multiclass_classifier_prediction - " + str(exc))
            pass

    def test_catboost_multiclass_classifier_training(self):
        """ Test training catboost as a multiclass classifier """
        try:
            with Factory() as factory:
                df, results = self.train_iris(factory)

                self.assertEqual(results["data"]["label"], "Species")
                self.assertEqual(results["data"]["source_records"], 150)
                self.assertEqual(results["data"]["training_records"], 120)
                self.assertEqual(results["data"]["test_records"], 30)

                self.assertEqual(len(results["data"]["classes"]), 3)
                self.assertEqual(results["data"]["classes"][0], "Iris-setosa")
                self.assertEqual(results["data"]["classes"][1], "Iris-versicolor")
                self.assertEqual(results["data"]["classes"][2], "Iris-virginica")

                self.assertEqual(results["parameters"]["loss_function"], "MultiClass")
                self.assertEqual(results["parameters"]["test_size"], 0.2)
                self.assertEqual(results["parameters"]["learning_rate"], 0.2)
                self.assertEqual(results["parameters"]["iterations"], 50)

                self.assertEqual(results["scores"]["accuracy_score"], 1.0)
                self.assertLess(results["scores"]["log_loss"], 0.10)

                self.assertEqual(len(results["scores"]["features_importance"]), 4)
                self.assertIn("PetalLengthCm", results["scores"]["features_importance"])
                self.assertIn("PetalWidthCm", results["scores"]["features_importance"])
                self.assertIn("SepalLengthCm", results["scores"]["features_importance"])
                self.assertIn("SepalWidthCm", results["scores"]["features_importance"])

                # model was saved?
                artifacts = factory.get_artifacts_directory()
                model_path = os.path.join(artifacts, "model.cbm")
                self.assertTrue(os.path.isfile(model_path))

        except Exception as exc:
            factory.error("test_catboost_multiclass_classifier - " + str(exc))
            pass

    def test_catboost_multiclass_classifier_training_classification_report(self):
        try:
            with Factory() as factory:
                df, results = self.train_iris(factory)

                classes = results["data"]["classes"]
                scores = results["scores"]
                self.assertIn("classification_report", scores)
                for class_name in classes:
                    self.assertIn(class_name, scores["classification_report"])
                    class_report = scores["classification_report"][class_name]
                    self.assertIn("f1-score", class_report)
                    self.assertIn("precision", class_report)
                    self.assertIn("recall", class_report)
                    self.assertIn("support", class_report)

                self.assertIn("confusion_matrix", scores)
                confusion_matrix = scores["confusion_matrix"]
                self.assertEqual(len(confusion_matrix), len(classes))
                for line in confusion_matrix:
                    self.assertEqual(len(line), len(classes))

        except Exception as exc:
            factory.error("test_catboost_multiclass_classifier_training_classification_report - " + str(exc))
            pass

    def test_catboost_multiclass_classifier_prediction(self):
        """ Test predictions with catboost as a binary classifier """
        try:
            with Factory() as factory:
                df, training = self.train_iris(factory)

                df_labels = df[["Species"]]
                df = df.drop(columns=["Species"])
                predict = catboost.run(df, action="endpoint/predict")

                # check to make sure predictions are from available labels
                self.assertIn("predictions", predict)
                self.assertEqual(len(predict["predictions"]), len(df))
                for prediction in predict["predictions"]:
                    self.assertIn(prediction, training["data"]["classes"])

                # make sure each record had each class scored
                self.assertIn("probabilities", predict)
                self.assertEqual(len(predict["probabilities"]), len(df))
                for probability in predict["probabilities"]:
                    for label_class in training["data"]["classes"]:
                        self.assertIn(label_class, probability)

                # check correctness of predictions
                # https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html
                report = sklearn.metrics.classification_report(df_labels, predict["predictions"], output_dict=True)
                self.assertGreater(report["Iris-setosa"]["f1-score"], 0.95)
                self.assertGreater(report["Iris-versicolor"]["f1-score"], 0.95)
                self.assertGreater(report["Iris-virginica"]["f1-score"], 0.95)

        except Exception as exc:
            factory.error("test_catboost_multiclass_classifier_prediction - " + str(exc))
            pass

    def test_catboost_regressor_training(self):
        """ Test training catboost as a regressor """
        try:
            with Factory() as factory:
                # boston data info here:
                # https://towardsdatascience.com/linear-regression-on-boston-housing-dataset-f409b7e4a155
                # bare bones, just run the plugin by itself w/o pipeline
                catboost = CatBoostPlugin(factory=factory, parameters={"learning_rate": 0.2})

                boston_dataset = load_boston()
                boston = pd.DataFrame(boston_dataset.data, columns=boston_dataset.feature_names)
                boston["MEDV"] = boston_dataset.target

                results = catboost.run(boston, action="recipe/train")

                self.assertIsNotNone(results)
                self.assertEqual(results["data"]["label"], "MEDV")  # median value
                self.assertEqual(results["data"]["source_records"], 506)
                self.assertEqual(results["data"]["training_records"], 404)
                self.assertEqual(results["data"]["test_records"], 102)

                # not a classifier
                self.assertFalse("classes" in results["data"])
                self.assertFalse("accuracy_score" in results["scores"])
                self.assertFalse("log_loss" in results["scores"])

                self.assertEqual(results["parameters"]["loss_function"], "RMSE")
                self.assertEqual(results["parameters"]["test_size"], 0.2)
                self.assertEqual(results["parameters"]["learning_rate"], 0.2)
                self.assertEqual(results["parameters"]["iterations"], 50)

                self.assertEqual(len(results["scores"]["features_importance"]), 13)
                self.assertGreater(results["scores"]["features_importance"]["AGE"], 8.0)
                self.assertGreater(results["scores"]["features_importance"]["DIS"], 8.0)
                self.assertGreater(results["scores"]["features_importance"]["LSTAT"], 20.0)

                self.assertIn("mean_abs_error", results["scores"])
                self.assertIn("median_abs_error", results["scores"])
                self.assertIn("sqrt_mean_squared_error", results["scores"])
                self.assertIn("mean_abs_error", results["scores"])

                # model was saved?
                artifacts = factory.get_artifacts_directory()
                model_path = os.path.join(artifacts, "model.cbm")
                self.assertTrue(os.path.isfile(model_path))

        except Exception as exc:
            factory.error("test_catboost_regressor - " + str(exc))
            pass

    def test_catboost_regressor_prediction(self):
        """ Test predictions with catboost as a regressor """
        try:
            with Factory() as factory:
                boston_dataset = load_boston()
                boston = pd.DataFrame(boston_dataset.data, columns=boston_dataset.feature_names)
                boston["MEDV"] = boston_dataset.target

                catboost = CatBoostPlugin(factory=factory, parameters={"learning_rate": 0.2})
                training = catboost.run(boston, action="recipe/train")
                self.assertIsNotNone(training)

                boston_dataset = load_boston()
                boston = pd.DataFrame(boston_dataset.data, columns=boston_dataset.feature_names)
                boston_labels = boston_dataset.target
                predict = catboost.run(boston, action="endpoint/predict")

                # check to make sure predictions are from available labels
                self.assertIn("predictions", predict)
                self.assertEqual(len(predict["predictions"]), len(boston))

                # https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html
                mae = sklearn.metrics.mean_absolute_error(boston_labels, predict["predictions"])
                self.assertLessEqual(mae, 3)

        except Exception as exc:
            factory.error("test_catboost_regressor_prediction - " + str(exc))
            pass
