""" Testing for ETL/Transformation components """
# pylint: disable=broad-except,unused-variable,missing-function-docstring,invalid-name,line-too-long,bad-continuation

import os
import random
import unittest
import logging
import datetime
import time

from collections import OrderedDict
from datetime import datetime, timedelta
from time import strftime
from typing import Text

import analitico_serving.serving
import analitico_serving.app

# number of examples in tests
S_SIZE = 100
M_SIZE = 1000
L_SIZE = 10 * 1000
XL_SIZE = 100 * 1000

# directory containing sample data used for tests
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "data/")


class ServingTest(unittest.TestCase):
    """ End to end test of serving container """

    # pre-run Automl recipe for unittest from workspace ws_y1ehlz2e
    run_automl_id = "au_3jj0vize"
    # if the automl is run again this model id must be updated
    blessed_model_id = "0002"
    # TODO: set per automl_id signed tokens
    api_token = "tok_demo2_xaffg23443d1"

    # pre-run Automl recipe for unittest from workspace ws_y1ehlz2e
    run_titanic_automl_id = "au_x3wl01lm"
    run_iris_automl_id = "au_xg37zkib"
    run_boston_automl_id = "au_nj1nh5xh"

    def setUp(self):
        super().setUp()
        logging.getLogger().setLevel(logging.INFO)

    def test_get_predictor(self):
        serving = analitico_serving.serving.Serving(self.run_automl_id, self.api_token)

        # get blessed model predictor
        predictor = serving.get_predictor()
        self.assertIsNotNone(predictor)
        self.assertEqual(serving.loaded_model_id, self.blessed_model_id)
        self.assertEqual(serving.blessed_model_id, self.blessed_model_id)
        self.assertIn(self.blessed_model_id, serving.available_models)
        self.assertLess(serving.last_check_on, datetime.utcnow())

        # get specific model predictor
        model_id = "0001"
        predictor = serving.get_predictor(model_id)
        self.assertIsNotNone(predictor)
        self.assertEqual(serving.loaded_model_id, model_id)
        self.assertNotEqual(serving.blessed_model_id, model_id)
        self.assertEqual(serving.blessed_model_id, self.blessed_model_id)
        self.assertIn(model_id, serving.available_models)

        # since last request wanted a specific model id,
        # now we expect to get the blessed model again
        predictor = serving.get_predictor()
        self.assertIsNotNone(predictor)
        self.assertEqual(serving.loaded_model_id, self.blessed_model_id)
        self.assertEqual(serving.blessed_model_id, self.blessed_model_id)

    def test_check_newer_model(self):
        serving = analitico_serving.serving.Serving(self.run_automl_id, self.api_token)

        # serving initialization try to load the blessed model
        last_check_on = serving.last_check_on
        self.assertLess(last_check_on, datetime.utcnow())

        # before Serving.CHECK_INTERVAL_SECONDS the check does nothing
        serving.check_newer_model()
        self.assertEqual(last_check_on, serving.last_check_on)

        # wait a minute and try again
        time.sleep(60)
        serving.check_newer_model()
        self.assertLess(serving.last_check_on, datetime.utcnow())
        self.assertLess(last_check_on, serving.last_check_on)

    def test_is_ready(self):
        serving = analitico_serving.serving.Serving(self.run_automl_id, self.api_token)
        self.assertTrue(serving.is_ready())

    def test_predict_binary(self):
        os.environ["ANALITICO_ITEM_ID"] = self.run_titanic_automl_id
        os.environ["ANALITICO_API_TOKEN"] = self.api_token

        instances = {
            "instances": [
                {
                    "Age": 34,
                    "ParentsChildrenAboard": 1,
                    "Name": "Mrs. John T (Ada Julia Bone) Doling",
                    "SiblingsSpousesAboard": 0,
                    "Fare": 23,
                    "Pclass": 2,
                    "Sex": "female",
                }
            ]
        }
        with analitico_serving.app.create_app().test_client() as client:
            response = client.post("/api/models/predict", json=instances)
            self.assertEqual(200, response.status_code)

            predictions = response.json.get("predictions")
            prediction = predictions[0]
            self.assertIn("scores", prediction)
            self.assertIn("classes", prediction)
            self.assertEqual(1, prediction["classes"][0])
            self.assertEqual(0.9178619911336535, prediction["scores"][0])

    def test_predict_multiclass(self):
        os.environ["ANALITICO_ITEM_ID"] = self.run_iris_automl_id
        os.environ["ANALITICO_API_TOKEN"] = self.api_token

        # multiple predictions
        instances = {
            "instances": [
                {"sepal_length": 7.3, "sepal_width": 2.9, "petal_width": 1.7, "petal_length": 6.3,},
                {"sepal_length": 4.9, "sepal_width": 2.5, "petal_width": 4.5, "petal_length": 1.7,},
            ]
        }
        with analitico_serving.app.create_app().test_client() as client:
            response = client.post("/api/models/predict", json=instances)
            self.assertEqual(200, response.status_code)

            predictions = response.json.get("predictions")
            prediction = predictions[0]
            self.assertIn("scores", prediction)
            self.assertIn("classes", prediction)
            self.assertEqual(["Setosa", "Versicolor", "Virginica"], prediction["classes"])
            self.assertEqual([0.3299835020271359, 0.3299835020271359, 0.3400329959457283], prediction["scores"])
            prediction = predictions[1]
            self.assertEqual(["Setosa", "Versicolor", "Virginica"], prediction["classes"])
            self.assertEqual([0.3333333333333333, 0.3333333333333333, 0.3333333333333333], prediction["scores"])

    def test_predict_regression(self):
        """ NOTE: This regression test may not work using debugger """
        os.environ["ANALITICO_ITEM_ID"] = self.run_boston_automl_id
        os.environ["ANALITICO_API_TOKEN"] = self.api_token

        # multiple predictions
        instances = {
            "instances": [
                {
                    "rad": 4,
                    "indus": 8.140000343322754,
                    "zn": 0,
                    "tax": 307,
                    "black": 376.7300109863281,
                    "crim": 1.3547199964523315,
                    "ptratio": 21,
                    "chas": 0,
                    "lstat": 13.039999961853027,
                    "age": 100,
                    "nox": 0.5379999876022339,
                    "dis": 4.175000190734863,
                    "index": 32,
                    "rm": 6.072000026702881,
                },
                {
                    "dis": 3.3778998851776123,
                    "index": 37,
                    "rm": 5.841000080108643,
                    "rad": 5,
                    "indus": 5.960000038146973,
                    "zn": 0,
                    "tax": 279,
                    "black": 377.55999755859375,
                    "crim": 0.09743999689817429,
                    "ptratio": 19.200000762939453,
                    "chas": 0,
                    "lstat": 11.40999984741211,
                    "age": 61.400001525878906,
                    "nox": 0.49900001287460327,
                },
            ]
        }
        with analitico_serving.app.create_app().test_client() as client:
            response = client.post("/api/models/predict", json=instances)
            self.assertEqual(200, response.status_code)

            predictions = response.json.get("predictions")
            self.assertEqual([15.071266180161375, 20.45848934488761], predictions)

    def test_predict_on_specific_model_id(self):
        os.environ["ANALITICO_ITEM_ID"] = self.run_titanic_automl_id
        os.environ["ANALITICO_API_TOKEN"] = self.api_token

        instances = {
            "instances": [
                {
                    "Age": 34,
                    "ParentsChildrenAboard": 1,
                    "Name": "Mrs. John T (Ada Julia Bone) Doling",
                    "SiblingsSpousesAboard": 0,
                    "Fare": 23,
                    "Pclass": 2,
                    "Sex": "female",
                }
            ]
        }
        with analitico_serving.app.create_app().test_client() as client:
            response = client.post("/api/models/0004/predict", json=instances)
            self.assertEqual(200, response.status_code)

    def test_invalid_input_json(self):
        os.environ["ANALITICO_ITEM_ID"] = self.run_titanic_automl_id
        os.environ["ANALITICO_API_TOKEN"] = self.api_token

        with analitico_serving.app.create_app().test_client() as client:
            instances = []
            response = client.post("/api/models/predict", json=instances)
            self.assertEqual(422, response.status_code)
            self.assertTrue(response.is_json)
            self.assertIn("error", response.get_json())

            instances = {}
            response = client.post("/api/models/predict", json=instances)
            self.assertEqual(422, response.status_code)
            self.assertTrue(response.is_json)
            self.assertIn("error", response.get_json())

            instances = {"instances": {"key": "not an array"}}
            response = client.post("/api/models/predict", json=instances)
            self.assertEqual(422, response.status_code)
            self.assertTrue(response.is_json)
            self.assertIn("error", response.get_json())

    def test_model_not_found(self):
        os.environ["ANALITICO_ITEM_ID"] = self.run_titanic_automl_id
        os.environ["ANALITICO_API_TOKEN"] = self.api_token

        with analitico_serving.app.create_app().test_client() as client:
            instances = {"instances": [{}]}
            response = client.post("/api/models/1234/predict", json=instances)
            self.assertEqual(404, response.status_code)
            self.assertTrue(response.is_json)
            self.assertIn("error", response.get_json())

if __name__ == "__main__":
    unittest.main()
