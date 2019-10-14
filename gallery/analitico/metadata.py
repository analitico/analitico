import os
import json
import logging
import collections

import sklearn
import sklearn.metrics

from analitico import logger
from analitico.utilities import read_json, save_json, get_dict_dot, set_dict_dot

# model metadata is saved in metadata.json
METADATA_FILENAME = "metadata.json"


def get_metadata(metadata_filename=METADATA_FILENAME):
    """ Returns metadata dictionary for current recipe. """
    return read_json(metadata_filename) if os.path.isfile(metadata_filename) else collections.OrderedDict()


def set_metric(
    metric: str,
    value,
    title: str = None,
    subtitle: str = None,
    priority: int = None,
    category: str = None,
    category_title: str = None,
    category_subtitle: str = None,
    metadata_filename=METADATA_FILENAME,
):
    """
    Collect a specific metric in the metadata file.

    These metrics can be useful to track performance of a trained model and can 
    also be shown in analitico's UI next to the trained models' information. A score
    has a machine readable id like number_of_lines and a value, eg. 100.

    Parameters:
    metric (str): The machine readable name of the metric, eg: number_of_records.
    value (object): The value of the metric can be an integer, float, string or a dictionary.
    title (str): Human readable name of the metric, eg: Number of records (optional).
    subtitle (str): Human readable name of the metric, eg: Number of records (optional).
    priority (int): Metric priority when shown in the UI (eg. 1 higher, 10 lower) (optional).
    category (str): A category id that should be used to group these metrics, eg. svc_classifier (optional).
    category_title (str): Human readable title for the category (optional).
    category_subtitle (str): A subtitle or tooltip for the category with more details (optional).
    metadata_filename (str): Path of metadata filename to be used if not the default one (optional).

    Returns:
    Nothing
    """
    metadata = get_metadata()

    if title or priority:
        value = {"value": value}
        if title:
            value["title"] = title
        if subtitle:
            value["subtitle"] = subtitle
        if priority:
            value["priority"] = priority

    key = f"scores.{category}.{metric}" if category else f"scores.{metric}"
    set_dict_dot(metadata, key, value)

    if category:
        if category_title:
            set_dict_dot(metadata, f"scores.{category}.title", category_title)
        if category_subtitle:
            set_dict_dot(metadata, f"scores.{category}.subtitle", category_subtitle)

    save_json(metadata, METADATA_FILENAME)


def set_model_metrics(
    y_true,
    y_pred,
    model: object = None,
    is_regressor: bool = None,
    is_classifier: bool = None,
    target_names=None,
    category: str = None,
    category_title: str = None,
    category_subtitle: str = None,
    metadata_filename: str = METADATA_FILENAME,
):
    """
    Save metrics related to a model's performance.

    Takes a model (derived from sklearn base estimator) and two array of values
    and predictions and saves a number of statistical scores regarding the accuracy
    of the predictions.

    Parameters:
    y_true (1d array-like): Ground truth (correct) labels/values.
    y_pred (1d array-line): Predicted labels or values, as returned by the model.
    model (object): An sklearn model that was used for predicting (optional).
    is_regressor (bool): True if model is a regressor, can also be inferred from model (optional).
    is_classifier (bool): True if model is a classifier, can also be inferred from model (optional).
    target_names (array): An array of labels for classifiers (optional).
    category (str): A category id that should be used to group these metrics, eg. svc_classifier (optional).
    category_title (str): Human readable title for the category (optional).
    category_subtitle (str): A subtitle or tooltip for the category with more details (optional).
    metadata_filename (str): Path of metadata filename to be used if not the default one (optional).

    Returns:
    Nothing
    """
    extras = {
        "category": category if category else "sklearn_metrics",
        "category_title": category_title if category_title else "Scikit Learn Metrics",
        "category_subtitle": category_subtitle if category_subtitle else None,
    }

    # ask sklearn what kind of model we have
    if isinstance(model, sklearn.base.BaseEstimator):
        is_regressor = sklearn.base.is_regressor(model) if is_regressor is None else is_regressor
        is_classifier = sklearn.base.is_classifier(model) if is_classifier is None else is_classifier
    else:
        # TODO we could probably guess the kind of model by just looking at the data
        logger.warning("set_model_metrics - we only support sklearn models for now")

    # There are many metrics for regression, we pick some basic ones...
    # https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics
    if is_regressor:
        set_metric(
            metric="mean_abs_error",
            value=round(sklearn.metrics.mean_absolute_error(y_true, y_pred), 5),
            title="Mean absolute regression loss",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html",
            **extras,
        )
        set_metric(
            metric="median_abs_error",
            value=round(sklearn.metrics.median_absolute_error(y_true, y_pred), 5),
            title="Median absolute error regression loss",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.median_absolute_error.html",
            **extras,
        )
        set_metric(
            metric="mean_squared_error",
            value=round(sklearn.metrics.mean_squared_error(y_true, y_pred), 5),
            title="Mean squared error regression loss",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_squared_error.html",
            **extras,
        )

    # https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics
    if is_classifier:
        classification_report = sklearn.metrics.classification_report(
            y_true, y_pred, target_names=target_names, output_dict=True
        )
        set_metric(
            metric="classification_report",
            value=classification_report,
            title="Classification report",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html",
            **extras,
        )
        # TODO could use target_names?
        confusion_matrix = sklearn.metrics.confusion_matrix(y_true, y_pred).tolist()
        set_metric(
            metric="confusion_matrix",
            value=confusion_matrix,
            title="Confusion matrix",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html",
            **extras,
        )

        # classification report has 3 fixed keys plus one per class
        is_binary_classifier = (len(classification_report) - 3) == 2

        if is_binary_classifier:
            set_metric(
                metric="log_loss",
                value=round(sklearn.metrics.log_loss(y_true, y_pred), 5),
                title="Log loss, aka logistic loss or cross-entropy loss",
                subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html",
                **extras,
            )

        # In multilabel classification, this function computes subset accuracy:
        # the set of labels predicted for a sample must exactly match the corresponding set of labels in y_true.
        set_metric(
            metric="accuracy_score",
            value=round(sklearn.metrics.accuracy_score(y_true, y_pred), 5),
            title="Accuracy classification score",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.accuracy_score.html",
            **extras,
        )

        # The precision is the ratio tp / (tp + fp) where tp is the number of true positives
        # and fp the number of false positives. The precision is intuitively the ability
        # of the classifier not to label as positive a sample that is negative.
        # The best value is 1 and the worst value is 0.
        set_metric(
            metric="precision_score_micro",
            value=round(sklearn.metrics.precision_score(y_true, y_pred, average="micro"), 5),
            title="Precision score (micro)",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html",
            **extras,
        )
        set_metric(
            metric="precision_score_macro",
            value=round(sklearn.metrics.precision_score(y_true, y_pred, average="macro"), 5),
            title="Precision score (macro)",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html",
            **extras,
        )
        set_metric(
            metric="precision_score_weighted",
            value=round(sklearn.metrics.precision_score(y_true, y_pred, average="weighted"), 5),
            title="Precision score (weighted)",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html",
            **extras,
        )

        # The recall is the ratio tp / (tp + fn) where tp is the number of true positives
        # and fn the number of false negatives. The recall is intuitively the ability
        # of the classifier to find all the positive samples.
        set_metric(
            metric="recall_score_micro",
            value=round(sklearn.metrics.recall_score(y_true, y_pred, average="micro"), 5),
            title="Recall score (micro)",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html",
            **extras,
        )
        set_metric(
            metric="recall_score_macro",
            value=round(sklearn.metrics.recall_score(y_true, y_pred, average="macro"), 5),
            title="Recall score (macro)",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html",
            **extras,
        )
        set_metric(
            metric="recall_score_weighted",
            value=round(sklearn.metrics.recall_score(y_true, y_pred, average="weighted"), 5),
            title="Recall score (weighted)",
            subtitle="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html",
            **extras,
        )
