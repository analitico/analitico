import os
import tempfile
import tempfile
import collections
import argparse
import base64
from datetime import datetime
from cacheout import Cache
from typing import Optional
import pickle

from rest_framework import status
from django.conf import settings

from analitico import AnaliticoException, logger
from api.models import ItemMixin, Recipe, Model, Workspace
from api.k8 import (
    k8_persistent_volume_deploy,
    k8_normalize_name,
    kubectl,
    K8_DEFAULT_NAMESPACE,
    K8_STAGE_PRODUCTION,
    K8_STAGE_STAGING,
    TEMPLATE_DIR,
)
from analitico.utilities import save_json, save_text, read_text, subprocess_run, id_generator, get_dict_dot

from analitico_automl import AutomlConfig
import analitico_automl.utilities
import analitico_automl.pipeline

import kfp
import kfp_server_api.rest
from tensorflow_serving.config import model_server_config_pb2
import tensorflow as tf
from google.protobuf import text_format, json_format

from tensorflow_transform.tf_metadata import dataset_schema
from tensorflow_transform.tf_metadata import schema_utils
from tensorflow.python.lib.io import file_io  # pylint: disable=g-direct-tensorflow-import
from tensorflow_metadata.proto.v0 import schema_pb2
import tensorflow_data_validation as tfdv
from tensorflow_transform import coders as tft_coders

from ml_metadata.metadata_store import metadata_store

import numpy as np

# each call to a Tensorflow predict endpoint requires the model schema to
# convert the request from json disctionary to base64 protobuf request.
# The memoize decorator below will cache the results of the schema file.
# https://cacheout.readthedocs.io/en/latest/cache.html#cacheout.cache.Cache.memoize
cache = Cache(maxsize=1024, ttl=2)

##
## AutoML
##


def get_metadata_store() -> metadata_store:
    """ Kubeflow Metadata Store database service connection """
    return analitico_automl.utilities.get_metadata_store(
        settings.KFP_METADATA_STORE_HOST,
        settings.KFP_METADATA_STORE_DB_NAME,
        settings.KFP_METADATA_STORE_USER,
        settings.KFP_METADATA_STORE_PASSWORD,
        mysql_port=settings.KFP_METADATA_STORE_PORT,
    )


def automl_run(item: ItemMixin, serving_endpoint=False) -> dict:
    """ 
    Request the execution on Kubeflow of the automl pipeline specified in the item object. 
    Create and return the Analitico Model object to map the execution in the Analitico flow.

    Arguments:
    ---------
        item : ItemMixin
            Analitico item object.
        serving_endpoint : bool
            When true, it's deployed a Tensorflow Serving image on Kubernetes for REST API prediction.
    
    """
    automl_config = item.get_attribute("automl")
    if not automl_config:
        raise AnaliticoException(
            f"Automl configuration is missing for item {item.id}", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    # used by KFP for saving the pipeline artifacts on the Analitico Drive
    # TODO: this is the first place where they are used. The deployment of
    #       the PV/PVC should be made when workspace is provisioned.
    k8_persistent_volume_deploy(item.workspace, storage_size="100Gi")

    with tempfile.NamedTemporaryFile("w+", suffix=".yaml") as output_filename:
        # inject the proper item's workspace id
        automl_config["workspace_id"] = item.workspace_id

        # setup the pipeline and generate its yaml
        analitico_automl.pipeline.get_kubeflow_pipeline_config(AutomlConfig(automl_config), output_filename.name)

        client = kfp.Client(settings.KFP_CLIENT_URL)

        # run name must be unique
        run_name = item.id + " " + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        # experiment name is created if missing, it is used if it exists
        experiment_name = item.id

        experiment = client.create_experiment(experiment_name)
        run = client.create_run_from_pipeline_package(
            pipeline_file=output_filename.name, arguments={}, run_name=run_name, experiment_name=experiment_name
        )

    # update the configuration with the id of
    # the run onbject which executed it and the
    # the experiment id it's been run into
    automl_config["run_id"] = run.run_id
    automl_config["experiment_id"] = experiment.id

    # update item with the last configuration
    item.set_attribute("automl", automl_config)
    item.save()

    # create the model with the applied automl configuration
    # in order to persist the configuration the pipeline
    # has been run with
    model = Model(workspace=item.workspace)
    model.set_attribute("automl_id", item.id)
    model.set_attribute("automl", automl_config)
    model.save()

    # deploy the endpoint for serving all workspace's automl models.
    if serving_endpoint:
        tensorflow_serving_deploy(item, model, stage=K8_STAGE_PRODUCTION)

    return model


@cache.memoize()
def automl_model_schema(item: ItemMixin, to_json: bool = False):
    """ 
    Retrieve and cache from Analitico Drive the TensorFlow model schema generated by 
    the TensorFlow pipeline.

    Returns
    -------
        Model schema in its protobuf format. If `to_json` is true they are
        returned in json format.
    """
    metadata_store = get_metadata_store()
    schema_uri = analitico_automl.utilities.get_pipeline_schema_uri(
        metadata_store, analitico_automl.utilities.get_pipeline_name(item.id), run_id=""
    )
    if not schema_uri:
        return None

    # on pods, the root of the workspace storage is mount in /mnt.
    # Here we need to strip it out from the path.
    schema_uri = schema_uri.replace("/mnt", "")

    # retrieve schema from workspace's drive
    workspace = item.workspace
    drive = workspace.storage.driver
    with tempfile.NamedTemporaryFile() as schema_file:
        drive.download(os.path.join(schema_uri, "schema.pbtxt"), schema_file.name)
        schema = schema_pb2.Schema()
        content = file_io.read_file_to_string(schema_file.name)
        text_format.Parse(content, schema)

    if to_json:
        schema = json_format.MessageToJson(schema)

    return schema


@cache.memoize()
def automl_model_statistics(item: ItemMixin, to_json: bool = False):
    """ 
    Retrieve and cache from Analitico Drive the TensorFlow Extended statistics 
    generated by TensorFlow pipeline.

    Returns
    -------
        Statistics in its protobuf format. If `to_json` is true they are
        returned in json format.
    """
    metadata_store = get_metadata_store()
    statistics_uri = analitico_automl.utilities.get_pipeline_statistics_uri(
        metadata_store, analitico_automl.utilities.get_pipeline_name(item.id), run_id=""
    )
    if not statistics_uri:
        return None

    # on pods, the root of the workspace storage is mount in /mnt.
    # Here we need to strip it out from the path.
    statistics_uri = statistics_uri.replace("/mnt", "")

    # retrieve statistics from workspace's drive
    workspace = item.workspace
    drive = workspace.storage.driver
    with tempfile.NamedTemporaryFile() as statistics_file:
        drive.download(os.path.join(statistics_uri, "stats_tfrecord"), statistics_file.name)
        stats = tfdv.load_statistics(input_path=statistics_file.name)

    if to_json:
        stats = json_format.MessageToJson(stats)

    return stats


def automl_model_examples(item: ItemMixin, quantity: int, to_json: bool = False):
    """ 
    Retrieve some examples from the dataset used to generate the model in the
    TensorFlow pipeline.

    Return
    ------
        Returns the tuple with examples and labels in json format if `to_json` is true,
        otherwise it returns the tuple of examples in nparray and None.
        Returns None in case of error.
    """
    metadata_store = get_metadata_store()
    uri = analitico_automl.utilities.get_pipeline_examples_uri(
        metadata_store, analitico_automl.utilities.get_pipeline_name(item.id), run_id="", split="eval"
    )
    if not uri:
        return None

    target_column = item.get_attribute("automl.target_column")
    assert target_column

    # on pods, the root of the workspace storage is mount in /mnt.
    # Here we need to strip it out from the path.
    uri = uri.replace("/mnt", "")

    # retrieve statistics from workspace's drive
    workspace = item.workspace
    drive = workspace.storage.driver
    with tempfile.NamedTemporaryFile() as dataset:
        files = drive.ls(uri)
        if len(files) < 2:
            return None
        # the first item is the folder itself
        drive.download(os.path.join(uri, files[1].name), dataset.name)

        examples = []
        labels = None

        raw_dataset = tf.data.TFRecordDataset([dataset.name], compression_type="GZIP")
        decoder = tfdv.TFExampleDecoder()
        for raw_record in raw_dataset.shuffle(quantity).take(quantity):
            examples.append(decoder.decode(raw_record.numpy()))

    if to_json:
        records = examples.copy()
        examples = []
        labels = []
        for record in records:
            example = {}
            for feature_name, feature_value in record.items():
                value = feature_value.item(0)
                if feature_value.dtype == np.object:
                    value = str(value, "utf-8")
                # collect example features and labels separately
                if feature_name == target_column:
                    labels.append({feature_name: value})
                else:
                    example[feature_name] = value
            examples.append(example)
        examples = json.dumps(examples)
        labels = json.dumps(labels)

    return examples, labels


def automl_model_preconditioner_statistics(item: ItemMixin, to_json: bool = False):
    """ 
    Retrieve the statistics generated by the preconditioner component in the
    TensorFlow pipeline.

    Return
    ------
        Returns the Analitico Statistics object loaded from a pickle file or the json
        representation of the object if `to_json` is true.
        Returns None in case of error.
    """
    metadata_store = get_metadata_store()
    uri = analitico_automl.utilities.get_pipeline_preconditioner_uri(
        metadata_store, analitico_automl.utilities.get_pipeline_name(item.id), run_id="", split="train"
    )
    if not uri:
        return None

    # on pods, the root of the workspace storage is mount in /mnt.
    # Here we need to strip it out from the path.
    uri = uri.replace("/mnt", "")

    # retrieve statistics from workspace's drive
    workspace = item.workspace
    drive = workspace.storage.driver
    with tempfile.NamedTemporaryFile() as f:
        files = drive.ls(uri)
        if len(files) < 2:
            return None
        # the first item is the folder itself
        drive.download(os.path.join(uri, files[1].name), f.name)

        with open(f.name, "rb") as pkl:
            data = pickle.load(pkl)

    if to_json:
        data = data.to_json()

    return data


def automl_convert_request_for_prediction(item: ItemMixin, content: dict) -> dict:
    """ 
    Convert Tensorflow instances values for prediction from json format to 
    protobuf-serialized and base64-encoded format required by TensorFlow Serving.

    Arguments
    ---------
        item : ItemMixin --- Analitico item object
        content : str
            A json string like: 
            { "instances": [ {"sepal_length":[6.4], "sepal_width":[2.8], "petal_length":[5.6], "petal_width":[2.2]} ] }

    Return
    ------
        A json string ready to be sent to the Tensorflow model for prediction.
        Eg:  { "instances": [ { "b64: "CmYKGAoMc2VwYWxfbGVuZ3RoEggSBgoEzczMQAoXCgtzZXBhbF93aWR0aBIIEgYKBDMzM0AKFwoLcGV0YWxfd2lkdGgSCBIGCgTNzAxAChgKDHBldGFsX2xlbmd0aBIIEgYKBDMzs0A=" } ] }
    """
    schema = automl_model_schema(item)
    if not schema:
        return None

    instances = content.get("instances")
    if not instances:
        raise AnaliticoException("`instances` key not found", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    examples_base64 = []
    if len(instances) > 0:
        index = 0
        serialized_examples = []
        for instance in instances:
            # is expected the user to specify all features required by the schem,
            # so the prediction is made on those features given in the request
            filtered_features = [feature for feature in schema.feature if feature.name in instances[index].keys()]
            del schema.feature[:]
            schema.feature.extend(filtered_features)

            raw_feature_spec = schema_utils.schema_as_feature_spec(schema).feature_spec
            raw_schema = dataset_schema.from_feature_spec(raw_feature_spec)
            proto_coder = tft_coders.ExampleProtoCoder(raw_schema)

            # tf.Transform requires values to be represented as Tensor (eg, [5.1])
            for feature_name in instance.keys():
                instance[feature_name] = [instance[feature_name]]

            example = proto_coder.encode(instance)
            serialized_examples.append(example)
            index = index + 1

        for example in serialized_examples:
            example_bytes = base64.b64encode(example).decode("utf-8")
            examples_base64.append('{ "b64": "%s" }' % example_bytes)

    json_request = '{ "instances": [' + ",".join(examples_base64) + "]}"
    return json_request


def tensorflow_models_config_update(item: ItemMixin, current_models_config: str):
    """ 
    Models are defined in a configuration file on a Kubernetes ConfigMap in a format 
    called Google Protobuf. 
    This method update the config from the Probuf format by defining the details of 
    the item's model name and path if not already set.

    Arguments:
    ----------
        item : ItemMixin
            Analitico item object the model is related to.
        current_models_config : str 
            Protobuf format of ModelServerConfig config.
            See: https://www.tensorflow.org/tfx/serving/serving_config#model_server_config_details
    """
    model_server_config = model_server_config_pb2.ModelServerConfig()
    text_format.Parse(current_models_config, model_server_config)

    exists = False
    for config in model_server_config.model_config_list.config:
        if config.name == item.id:
            exists = True

    if not exists:
        # define model's specs
        config_model = model_server_config.model_config_list.config.add()
        config_model.name = item.id
        config_model.base_path = f"/mnt/automls/{item.id}/serving"
        config_model.model_platform = "tensorflow"

    config_content = text_format.MessageToString(model_server_config)
    return config_content


##
## Kubeflow
##


def kf_pipeline_runs_get(item: ItemMixin, run_id: str = None, list_page_token: str = "") -> dict:
    """ 
    Return the single Kubeflow run object with the execution status of the pipeline on Kubeflow
    or the list of runs for a given experiment id.

    Arguments
    ---------
        item : ItemMixin
            Analitico item object.
        run_id : str
            Optional. Kubeflow object run id relative to the desidered execution of the pipeline.
            If None, it is returned the list of runs for the experiment identified by the item's id.
        list_page_token : str
            Optional. 
            Token for pagination of the list of runs.    
    """
    try:
        client = kfp.Client(settings.KFP_CLIENT_URL)
        if run_id:
            run = client.get_run(run_id)
            return run.to_dict()
        else:
            # check user access to the experiment specified in the item's attributes.
            # Experiments are identified by their id and the recipe id
            experiment_id = item.get_attribute("automl.experiment_id")
            experiment = client.get_experiment(experiment_id=experiment_id)
            if experiment.name != item.id:
                raise AnaliticoException(
                    "Recipe was not run in the given experiment id", status_code=status.HTTP_403_FORBIDDEN
                )

            runs = client.list_runs(experiment_id=experiment_id, page_token=list_page_token)
            return runs.to_dict()
    except kfp_server_api.rest.ApiException as e:
        raise AnaliticoException("Cannot retrieve the run object", status_code=e.status) from e


def tensorflow_serving_deploy(item: ItemMixin, target: ItemMixin, stage: str = K8_STAGE_PRODUCTION) -> dict:
    """ Deploy a TensorFlow Serving image for serving recipes' TensorFlow model in a workspace.

    TensorFlow Serving image is able to serve multiple models with multiple versions.
    We use this feature so we deploy a single endpoint for prediction, named with the workspace
    id for serving all workspace's recipes' models.
    Eg: https://ws-automl-tfserving.cloud.analitico.ai/v1/models/rx_iris
    """
    try:
        assert item.workspace
        workspace_id = item.workspace.id

        from api.k8 import k8_customize_and_apply

        # name of service we are deploying, eg: ws-001-tfserving, ws-001-tfserving-staging
        stage_suffix = "-{stage}" if stage != K8_STAGE_PRODUCTION else ""
        name = workspace_id + "-tfserving" + stage_suffix
        service_name = k8_normalize_name(name)
        service_namespace = "cloud"
        workspace_id_slug = k8_normalize_name(workspace_id)

        configs = collections.OrderedDict()
        configs["service_name"] = service_name
        configs["service_namespace"] = service_namespace
        configs["workspace_id"] = workspace_id
        configs["workspace_id_slug"] = workspace_id_slug
        configs["item_id"] = item.id
        configs["controller_name"] = service_name
        # TensorFlow Serving 1.15.0
        configs[
            "image_name"
        ] = "tensorflow/serving@sha256:c25e808561b6983031f1edf080d63d5a2a933b47e374ce6913342f5db4d1280c"

        try:
            config_map, _ = kubectl(
                service_namespace, "get", f"configMap/tensorflow-serving-config-{workspace_id_slug}"
            )
            current_models_config = get_dict_dot(config_map, "data", {}).get("models.config", "")
        except Exception as e:
            if e.status_code == status.HTTP_404_NOT_FOUND:
                # config map not found
                current_models_config = ""
            else:
                raise e

        protobuf_model_config = tensorflow_models_config_update(item, current_models_config)
        # align all lines in order to be correctly formatted and accepted on the yaml data attribute
        protobuf_model_config = "    ".join(protobuf_model_config.splitlines(True))
        configs["protobuf_model_config"] = protobuf_model_config

        # deploy the main service resource
        template_filename = os.path.join(TEMPLATE_DIR, "tfserving-service-template.yaml")
        service_json = k8_customize_and_apply(template_filename, **configs)

        # retrieve existing services
        services = target.get_attribute("service", {})

        configs["owner_uid"] = get_dict_dot(service_json, "metadata.uid")

        # deploy all the other service related resources
        template_filename = os.path.join(TEMPLATE_DIR, "tfserving-template.yaml")
        k8_customize_and_apply(template_filename, **configs)

        # save deployment information inside item, endpoint and job
        attrs = collections.OrderedDict()
        attrs["type"] = "analitico/service"
        attrs["name"] = service_name
        attrs["namespace"] = service_namespace
        attrs["url"] = get_dict_dot(service_json, "status.url", None)
        attrs["response"] = service_json

        # item's service dictionary can have a 'production' and a 'staging' collection or more
        services[stage] = attrs
        target.set_attribute("service", services)
        target.save()

        logger.debug(json.dumps(attrs, indent=4))
        return attrs
    except AnaliticoException as exc:
        raise exc
    except Exception as exc:
        raise AnaliticoException(f"Could not deploy {item.id} because: {exc}") from exc

