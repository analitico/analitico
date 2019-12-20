import os
import tempfile
import collections
import json
from datetime import datetime

from rest_framework import status

from analitico import AnaliticoException, logger
from api.models import ItemMixin, Recipe, Model, Workspace
from api.k8 import k8_normalize_name, kubectl, K8_DEFAULT_NAMESPACE, K8_STAGE_PRODUCTION, K8_STAGE_STAGING, TEMPLATE_DIR
from analitico.utilities import save_json, save_text, read_text, subprocess_run, id_generator, get_dict_dot

from analitico_automl import AutomlConfig
from analitico_automl import pipelines

import kfp
from tensorflow_serving.config import model_server_config_pb2
from google.protobuf import text_format


##
## AutoML
##


def automl_run(item: ItemMixin, serving_endpoint=False) -> dict:
    """ 
    Request the execution on Kubeflow of the automl pipeline specified in the item object. 
    Create and return the model object to map the execution in the Analitico flow.

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

    with tempfile.NamedTemporaryFile("w+", suffix=".yaml") as output_filename:
        # inject the proper item's workspace id
        automl_config["workspace_id"] = item.workspace_id

        # setup the pipeline and generate its yaml
        pipelines.get_kubeflow_pipeline_config(AutomlConfig(automl_config), output_filename.name)

        client = kfp.Client("staging1.analitico.ai:31061")

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
    model.set_attribute("recipe_id", item.id)
    model.set_attribute("automl", automl_config)
    model.save()

    # deploy endpoint for serving all workspace's automl models
    if serving_endpoint:
        tensorflow_serving_deploy(item, model, stage=K8_STAGE_PRODUCTION)

    return model


##
## Kubeflow
##

def kf_update_tensorflow_models_config(item: ItemMixin, current_models_config: str):
    """ 
    Models are defined in a configuration file on a Kubernetes 
    ConfigMap in a format called Google Protobuf. 
    This method update the config from the Probuf format by 
    defining the details of the item's model name and path if not already set.

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
        config_model.base_path = f"/mnt/automl/{item.id}/serving"
        config_model.model_platform = "tensorflow"

    config_content = text_format.MessageToString(model_server_config)
    return config_content
    

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
    client = kfp.Client("staging1.analitico.ai:31061")
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


def tensorflow_serving_deploy(item: ItemMixin, target: ItemMixin, stage: str = K8_STAGE_PRODUCTION) -> dict:
    """ Deploy a Tensorflow Serving image for a recipe built with a TensorFlow model """
    try:
        assert item.workspace
        workspace_id = item.workspace.id

        from api.k8 import k8_customize_and_apply

        # name of service we are deploying
        stage_suffix = "-{stage}" if stage != K8_STAGE_PRODUCTION else ""
        name = workspace_id + stage_suffix
        service_name = k8_normalize_name(name)
        service_namespace = "cloud"
        
        config = collections.OrderedDict()
        config["service_name"] = service_name
        config["service_namespace"] = service_namespace
        config["workspace_id"] = workspace_id
        config["workspace_id_slug"] = k8_normalize_name(workspace_id)
        config["item_id"] = item.id
        config["controller_name"] = f"{service_name}-{id_generator(5)}"
        # TensorFlow Serving 1.15.0
        config["image_name"] = "tensorflow/serving@sha256:c25e808561b6983031f1edf080d63d5a2a933b47e374ce6913342f5db4d1280c"
        
        try:
            config_map, _ = kubectl(service_namespace, "get", f"configMap/tensorflow-serving-config-{workspace_id}")
            current_models_config = get_dict_dot(config_map, "models.config", "")
        except Exception as e:
            if e.status_code == status.HTTP_404_NOT_FOUND:
                # config map not found
                current_models_config = ""
            else:
                raise e

        protobuf_model_config = kf_update_tensorflow_models_config(item, current_models_config)
        # align all lines in order to be correctly formatted and accepted on the yaml data attribute
        protobuf_model_config = '    '.join(protobuf_model_config.splitlines(True))
        config["protobuf_model_config"] = protobuf_model_config
        
        # deploy the main service resource
        template_filename = os.path.join(TEMPLATE_DIR, "service-tensorflow-service-template.yaml")
        service_json = k8_customize_and_apply(template_filename, **config)

        # retrieve existing services
        services = target.get_attribute("service", {})

        config["owner_uid"] = get_dict_dot(service_json, "metadata.uid")

        # deploy all the other service related resources
        template_filename = os.path.join(TEMPLATE_DIR, "service-tensorflow-template.yaml")
        k8_customize_and_apply(template_filename, **config)

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

