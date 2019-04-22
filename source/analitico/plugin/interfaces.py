import collections
import pandas as pd
import os.path
import multiprocessing
import os
import string
import random

from abc import ABC, abstractmethod

# Design patterns:
# https://github.com/faif/python-patterns

from analitico.mixin import AttributeMixin
from analitico.factory import Factory
from analitico.utilities import time_ms, save_json, read_json, get_runtime_brief
from analitico.schema import apply_schema
from analitico.constants import PLUGIN_PREFIX

##
## IPlugin - base class for all plugins
##


class IPlugin(ABC, AttributeMixin):
    """ Abstract base class for Analitico plugins """

    class Meta:
        """ Plugin metadata is exposed in its inner class """

        name = None

    # Factory that provides runtime services to the plugin (eg: loading assets, etc)
    factory: Factory = None

    @property
    def id(self):
        return self.get_attribute("id")

    @property
    def name(self):
        assert self.Meta.name
        return self.Meta.name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "factory" in kwargs:
            self.factory = kwargs["factory"]

    def activate(self, *args, **kwargs):
        """ Called when the plugin is initially activated """
        pass

    @abstractmethod
    def run(self, *args, action=None, **kwargs):
        """ Run will do in the subclass whatever the plugin does, 'action' parameter optional """
        pass

    def deactivate(self, *args, **kwargs):
        """ Called before the plugin is deactivated and finalized """
        pass

    def __str__(self):
        return self.name

    # Utility methods

    def drop_selected_rows(self, df, df_dropped, message=None):
        """ Drops df_dropped rows from dp in place, logs action """
        started_on = time_ms()
        rows_before = len(df.index)
        if rows_before < 1:
            self.warning("Can't drop rows where '%s' because dataframe is empty", message)
            return df
        df.drop(df_dropped.index, inplace=True)
        if message:
            rows_after = len(df.index)
            rows_dropped = rows_before - rows_after
            msg = "Dropped rows where '%s', rows before: %d, after: %d, dropped: %d (%.2f%%) in %d ms"
            self.info(
                msg,
                message,
                rows_before,
                rows_after,
                rows_dropped,
                (100.0 * rows_dropped) / rows_before,
                time_ms(started_on),
            )
        return df

    def drop_na_rows(self, df, column):
        """ Drops rows with null values in given column, logs action """
        started_on = time_ms()
        rows_before = len(df.index)
        if rows_before < 1:
            self.warning("Can't drop null '%s' rows because dataframe is empty", column)
            return df
        df.dropna(subset=[column], inplace=True)
        rows_after = len(df.index)
        rows_dropped = rows_before - rows_after
        msg = "Dropped rows where '%s' is null, rows before: %d, after: %d, dropped: %d (%.2f%%) in %d ms"
        self.info(
            msg,
            column,
            rows_before,
            rows_after,
            rows_dropped,
            (100.0 * rows_dropped) / rows_before,
            time_ms(started_on),
        )
        return df

    # Logging

    @property
    def logger(self):
        """ Logger that can be used by the plugin to communicate errors, etc with host """
        return self.factory.logger

    def info(self, msg, *args, **kwargs):
        self.factory.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.factory.warning(msg, *args, **kwargs)

    def error(self, msg, *args, exception=None, **kwargs):
        self.factory.error(msg, *args, plugin=self, exception=exception, **kwargs)

    def exception(self, msg, *args, exception=None, **kwargs):
        self.factory.exception(msg, *args, plugin=self, exception=exception, **kwargs)

    def __str__(self):
        id = self.get_attribute("id")
        return self.Meta.name + ":" + id if id else self.Meta.name


##
## IDataframeSourcePlugin - base class for plugins that create dataframes
##


class IDataframeSourcePlugin(IPlugin):
    """ A plugin that creates a pandas dataframe from a source (eg: csv file, sql query, etc) """

    class Meta(IPlugin.Meta):
        inputs = None
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    @abstractmethod
    def run(self, *args, action=None, **kwargs):
        """ Run creates a dataset from the source and returns it """
        pass


##
## IDataframePlugin - base class for plugins that manipulate pandas dataframes
##


class IDataframePlugin(IPlugin):
    """
    A plugin that takes a pandas dataframe as input,
    manipulates it and returns a pandas dataframe
    """

    class Meta(IPlugin.Meta):
        inputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]
        outputs = [{"name": "dataframe", "type": "pandas.DataFrame"}]

    def run(self, *args, action=None, **kwargs) -> pd.DataFrame:
        assert isinstance(args[0], pd.DataFrame)
        return args[0]


##
## IAlgorithmPlugin - base class for machine learning algorithms that produce trained models
##

ALGORITHM_TYPE_REGRESSION = "ml/regression"
ALGORITHM_TYPE_BINARY_CLASSICATION = "ml/binary-classification"
ALGORITHM_TYPE_MULTICLASS_CLASSIFICATION = "ml/multiclass-classification"
ALGORITHM_TYPE_ANOMALY_DETECTION = "ml/anomaly-detection"
ALGORITHM_TYPE_CLUSTERING = "ml/clustering"


class IAlgorithmPlugin(IPlugin):
    """ An algorithm used to create machine learning models from training data """

    class Meta(IPlugin.Meta):
        inputs = [{"name": "train", "type": "pandas.DataFrame"}, {"name": "test", "type": "pandas.DataFrame|none"}]
        outputs = [{"name": "model", "type": "dict"}]

    def _run_train(self, *args, **kwargs):
        """ 
        When an algorithm runs it always takes in a dataframe with training data,
        it may optionally have a dataframe of validation data and will return a dictionary
        with information on the trained model plus a number of artifacts.
        """
        assert isinstance(args[0], pd.DataFrame)
        started_on = time_ms()
        results = collections.OrderedDict(
            {
                "type": "analitico/training",
                "plugins": {
                    "training": self.Meta.name,  # plugin used to train model
                    "prediction": self.Meta.name,  # plugin to be used for predictions (usually the same)
                },
                "data": {},  # number of records, etc
                "parameters": {},  # model parameters, hyperparameters
                "scores": {},  # training scores
                "performance": get_runtime_brief(),  # time elapsed, cpu, gpu, memory, disk, etc
            }
        )

        train = args[0]
        test = args[1] if len(args) > 1 else None
        results = self.train(train, test, results, *args, **kwargs)

        # finalize results and save as training.json
        results["performance"]["total_ms"] = time_ms(started_on)
        artifacts_path = self.factory.get_artifacts_directory()
        results_path = os.path.join(artifacts_path, "training.json")
        save_json(results, results_path)
        self.info("saved %s (%d bytes)", results_path, os.path.getsize(results_path))
        return results

    def _run_predict(self, *args, **kwargs):
        """ 
        When an algorithm runs it always takes in a dataframe with training data,
        it may optionally have a dataframe of validation data and will return a dictionary
        with information on the trained model plus a number of artifacts.
        """
        # assert isinstance(args[0], pandas.DataFrame) # custom models may take json as input
        data = args[0]

        artifacts_path = self.factory.get_artifacts_directory()
        training = read_json(os.path.join(artifacts_path, "training.json"))
        assert training

        started_on = time_ms()
        results = collections.OrderedDict(
            {
                "type": "analitico/prediction",
                # "endpoint_id": None,
                # "model_id": None,
                # "job_id": None,
                # "records": None,  # processed (augmented) data will be added by IAlgorithm
                # "predictions": None,  # predictions
                # "probabilities": None,
                "performance": get_runtime_brief(),  # time elapsed, cpu, gpu, memory, disk, etc
            }
        )

        # force schema like in training data
        if isinstance(data, pd.DataFrame):
            schema = training["data"]["schema"]
            data = apply_schema(data, schema)

        # load model, calculate predictions
        results = self.predict(data, training, results, *args, **kwargs)
        results["performance"]["total_ms"] = time_ms(started_on)

        results_path = os.path.join(artifacts_path, "results.json")
        save_json(results, results_path)

        return results

    def run(self, *args, action=None, **kwargs):
        """ Algorithm can run to train a model or to predict from a trained model """
        if action.endswith("train"):
            return self._run_train(*args, **kwargs)
        if action.endswith("predict"):
            return self._run_predict(*args, **kwargs)
        self.error("unknown action: %s", action)
        raise PluginError("IAlgorithmPlugin - action should be /train or /predict")

    @abstractmethod
    def train(self, train, test, results, *args, **kwargs):
        """ Train with algorithm and given data to produce a trained model """
        pass

    @abstractmethod
    def predict(self, data, training, results, *args, **kwargs):
        """ Return predictions from trained model """
        pass


##
## IGroupPlugin
##


class IGroupPlugin(IPlugin):
    """ 
    A composite plugin that joins multiple plugins into a functional block,
    for example a processing pipeline made of plugins or a graph workflow. 
    
    *References:
    https://en.wikipedia.org/wiki/Composite_pattern
    https://infinitescript.com/2014/10/the-23-gang-of-three-design-patterns/
    """

    plugins = []

    def __init__(self, *args, plugins=[], **kwargs):
        """ Initialize group and create all this plugin's children """
        super().__init__(*args, **kwargs)
        self.plugins = []
        for plugin in plugins:
            if isinstance(plugin, dict):
                plugin = self.factory.get_plugin(**plugin)
            plugin.factory = self.factory  # use same factory as parent plugin
            self.plugins.append(plugin)


##
## PluginError
##


class PluginError(Exception):
    """ Exception generated by a plugin; carries plugin info, inner exception """

    # Plugin error message
    message: str = None

    # Plugin that generated this error (may not be defined)
    plugin: IPlugin = None

    def __init__(self, message, plugin: IPlugin = None, exception: Exception = None):
        super().__init__(message, exception)
        self.message = message
        if plugin:
            self.plugin = plugin
            plugin.logger.error(message)

    def __str__(self):
        if self.plugin:
            return self.plugin.Meta.name + ": " + self.message
        return self.message


##
## @plugin registration helper
##


def plugin(cls):
    """ Use this @plugin decorator on IPlugin classes to register them automatically """
    Factory.register_plugin(cls)
    return cls


def generate_plugin_id():
    """ Generates a random id that is suitable for a plugin instance """
    return PLUGIN_PREFIX + "".join(random.choice(string.hexdigits) for i in range(8))


def apply_plugin_id(plugin_conf: dict):
    """ Checks if the plugin configuration has IDs and if not generates them for this plugin and its children. True if applied, False unchanged. """
    applied = False
    if plugin_conf:
        if "id" not in plugin_conf:
            plugin_conf["id"] = generate_plugin_id()
            applied = True
        if "plugins" in plugin_conf:
            for child_conf in plugin_conf["plugins"]:
                if apply_plugin_id(child_conf):
                    applied = True
    return applied
