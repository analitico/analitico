import os
import requests
import logging
import shutil
from datetime import datetime, timedelta
import tempfile

from autogluon import TabularPrediction as task

from analitico_serving.exceptions import AnaliticoException

# how often check for new model
CHECK_INTERVAL_SECONDS = 60


class Serving:

    # predictor is loaded with the last requested version
    predictor: task.Predictor = None
    # reports the model_id loaded for the predictor
    loaded_model_id: str = None
    # last available model
    blessed_model_id: str = None
    # all local available model versions
    available_models: [str] = []

    last_check_on: datetime = None

    def __init__(self, automl_id: str, api_token: str):
        self.automl_id = automl_id
        self.api_token = api_token
        self.models_path = "/models/" + automl_id
        if not os.path.exists(self.models_path):
            os.makedirs(self.models_path)

        # initialize serving
        self.load_blessed_model()

    def get_predictor(self, model_id: str = None):
        if model_id:
            self.load_model(model_id)
        else:
            self.load_blessed_model()

        return self.predictor

    def load_model(self, model_id: str) -> task.Predictor:
        """ Load specific model """
        if self.loaded_model_id == model_id:
            logging.debug(f"model {model_id} already loaded")
            return self.predictor

        # needs to be retrieved
        if model_id not in self.available_models:
            self.download_model(model_id)

        return self.load_predictor(model_id)

    def load_blessed_model(self) -> task.Predictor:
        """ Load the last model and check if a newer is available """
        self.check_newer_model()

        if not self.blessed_model_id:
            logging.error("blessed model id is not set")
            return None

        if self.loaded_model_id == self.blessed_model_id:
            logging.debug("blessed model is already loaded")
            return self.predictor

        return self.load_predictor(self.blessed_model_id)

    def check_newer_model(self) -> str:
        first_run = self.last_check_on is None

        if first_run or datetime.now() > self.last_check_on + timedelta(0, CHECK_INTERVAL_SECONDS):
            logging.info("check for newer model")
            self.last_check_on = datetime.utcnow()

            try:
                automl_config = self.download_automl_config()
            except Exception as e:
                logging.error(f"model check failed - response\n: {e}")
                logging.error("skipping model check because of an error while downloading automl.json")
                return self.predictor

            blessed_model_id = automl_config.get("blessed_model_id")
            if not blessed_model_id:
                logging.error("no model available. Has the automl ever run before?")
                return self.predictor

            self.blessed_model_id = blessed_model_id
            try:
                if blessed_model_id not in self.available_models:
                    logging.info(f"newer model {blessed_model_id} is available")
                    self.download_model(blessed_model_id)
            except Exception as e:
                logging.error(f"model check failed - response\n: {e}")
                logging.error("skipping model check because of an error while downloading the model's archive file")
                return self.predictor

        return self.blessed_model_id

    def load_predictor(self, model_id: str) -> task.Predictor:
        # learner.pkl keeps track of path starting from the
        # output_directory specified in the fit() method.
        # So this output_directory must be the same used in fit().
        # First we need to move the currenty directory
        # where models are stored.
        os.chdir(self.get_model_path(model_id))
        self.predictor = task.load("./")
        self.loaded_model_id = model_id
        logging.info(f"serving model {model_id} for {self.automl_id}")
        return self.predictor

    def download_automl_config(self) -> dict:
        """ Download automl config json """
        headers = {"Authorization": "Bearer " + self.api_token}
        response = requests.get(
            f"https://analitico.ai/api/automls/{self.automl_id}/files/models/automl.json", headers=headers
        )
        if response.status_code != 200:
            raise AnaliticoException(response.content, status_code=404)
        return response.json()

    def download_model(self, model_id: str) -> str:
        """ Download and extract the model's archive file """
        logging.debug(f"download model {model_id}")
        headers = {"Authorization": "Bearer " + self.api_token}
        url = f"https://analitico.ai/api/automls/{self.automl_id}/files/models/{model_id}.zip"
        with tempfile.NamedTemporaryFile("wb", suffix=".zip") as f:
            with requests.get(url, headers=headers) as r:
                if r.status_code != 200:
                    raise AnaliticoException(r.content, status_code=r.status_code)
                f.write(r.content)
            # extract model from archive
            logging.debug(f"model archive downloaded in {f.name}")
            shutil.unpack_archive(f.name, extract_dir=self.get_models_path())
            logging.debug(f"model archive unpacked in {self.get_models_path()}")

            self.available_models.append(model_id)

            return self.get_model_path(model_id)

    def get_models_path(self) -> str:
        return self.models_path

    def get_model_path(self, model_id: str) -> str:
        return os.path.join(self.get_models_path(), model_id)

    def is_ready(self) -> bool:
        """ Ready when a model's predictor is available """
        return self.predictor is not None
