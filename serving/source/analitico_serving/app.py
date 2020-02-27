##
# Script executed by gunicorn for the prediction services
##

import os
import simplejson as json
import logging
import pandas as pd

import analitico_serving.serving
import analitico_serving.utilities
import analitico_serving.fluentd
from analitico_serving.exceptions import AnaliticoException

from flask import Flask
from flask import request, Response
from flask_cors import CORS

from autogluon import TabularPrediction as task

# pylint: disable=no-member
# pylint: disable=no-value-for-parameter

# setup logging so that we replace python's root logger with a new handler that
# can format messages as json in a way that is easily readable by our fluentd
# while preserving the log messages' metadata (eg. level, function, line, logger, etc)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": analitico_serving.fluentd.FluentdFormatter, "format": "%(asctime)s %(message)s"}},
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stderr",
        }
    },
    "root": {"handlers": ["default"]},
}
logging.config.dictConfig(LOGGING_CONFIG)
logging.getLogger().setLevel(int(os.getenv("LOG_LEVEL", logging.INFO)))


def create_app():
    automl_id = os.getenv("ANALITICO_ITEM_ID")
    token = os.getenv("ANALITICO_API_TOKEN")
    assert automl_id, "Analitico Automl id is not defined"
    assert token, "missing Analitico token for api requests"

    #
    # Start Flask App
    #

    app = Flask(__name__)
    app.logger.info("Starting Serving")
    # enable CORS requests for all domains on all routes
    CORS(app)

    serving = analitico_serving.serving.Serving(automl_id, token)

    #
    # Configure App Routes
    #
    @app.route("/api/models/<model_id>/predict", methods=["POST"])
    @app.route("/api/models/predict", methods=["POST"])
    def predict(model_id: str = None):
        try:
            data = request.get_json()
            instances = data.get("instances") if isinstance(data, dict) else None
            if not instances or not isinstance(instances, list):
                raise AnaliticoException("please specify a list of `instances` to predict", status_code=422)
            app.logger.debug(instances)

            predictor = serving.get_predictor(model_id)
            if not predictor:
                logging.error("model not found")
                raise AnaliticoException("model not found", status_code=404)

            dataframe = pd.DataFrame(instances)
            y_pred = predictor.predict(dataframe, model="NeuralNetRegressor").tolist()

            if predictor.problem_type == "regression":
                results = y_pred
            else:
                # for multiclass and binary prediction we
                # output results with classes and scores,
                # eg: {"scores":[0,1,7.27956298e-27],"classes":["Setosa","Virginica","Versicolor"]}
                results = []
                index = 0
                y_pred_proba = predictor.predict_proba(dataframe).tolist()
                for i in range(len(instances)):
                    # we only know the predicted binary label and it's confidence
                    if predictor.problem_type == "binary":
                        # binary
                        class_labels = [y_pred[index]]
                        # confidence in binary is exposed as follow:
                        # "red" (0) --- 0.5 --- "blue" (1)
                        # but we prefer to output the confidence value
                        # as a percentage between 0 (less confident) to 1 (very confident)
                        scores = [max(y_pred_proba[index], 1 - y_pred_proba[index])]
                        result = {"classes": class_labels, "scores": scores}
                    else:
                        # multiclass
                        class_labels = predictor.class_labels
                        scores = y_pred_proba[index]
                        result = {"classes": class_labels, "scores": scores}

                    results.append(result)
                    index += 1

            body = '{ "predictions": ' + json.dumps(results) + " }"
            return Response(body, status=200, mimetype="application/json")

        except Exception as exception:
            response = {"error": analitico_serving.utilities.exception_to_dict(exception)}
            status = int(response["error"].get("status", 500))
            response_json = json.dumps(response)
            logging.error(response_json)
            return Response(response_json, status=status, mimetype="application/json")

    @app.route("/health", methods=["GET", "POST"])
    def health():
        # https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-probes/#define-a-liveness-http-request
        return "ready"

    @app.route("/ready", methods=["GET", "POST"])
    def ready():
        # https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-probes/#define-a-liveness-http-request
        return serving.get_predictor() is not None

    #
    # Return App
    #

    return app
