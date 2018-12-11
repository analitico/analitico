
import os.path

from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ParseError

import analitico.models
import analitico.utilities
import analitico.storage
import api.models
import api.utilities

from analitico.utilities import logger
from api.utilities import time_ms, api_get_parameter, api_check_authorization

import s24.models

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

# TODO fix styles, logos, etc
# https://www.django-rest-framework.org/topics/browsable-api/


MODELS = {
    # generic regressor from tabular data
    'tabular-regressor-model': analitico.models.TabularRegressorModel,
    # model to estimate s24 order time    
    's24-order-time-model': s24.models.OrderTimeModel,
    # model to sort s24 orders based on supermarket layout    
    's24-order-sorting-model': s24.models.OrderSortingModel,
    # model to predict if items may be out of stock    
    's24-out-of-stock-model': s24.models.OutOfStockModel,
}

##
## Utility methods
##

def get_request_data_and_query(request):
    data = request.data.copy()
    for key, value in request.GET.items():
        data[key] = value if len(value) != 1 else value[0]
    return data


def get_project_model(project_id: str) -> (api.models.Project, analitico.models.AnaliticoModel):
    """ Returns an initialized model for the given project """
    try:
        project = api.models.Project.objects.get(pk=project_id)
        settings = project.settings
        # TODO check access permissions
        try:
            return project, MODELS[settings['model_id']](settings)
        except Exception:
            pass
        return project, MODELS[project_id + '-model'](settings)
    except ObjectDoesNotExist:
        raise NotFound('Model for ' + project_id + ' was not found')


def project_response(project):
    """ Return an API Response containing the given Project """
    return Response({
        'data': {
            'project_id': project.id,
            'training_id': project.training_id,
            'settings': project.settings,
            'notes': project.notes,
            'created_at': project.created_at,
            'updated_at': project.updated_at
        }
    })


def training_response(training):
    """ Return an API Response containing the given Training """
    return Response({
        'data': {
            'project_id': training.project.id,
            'training_id': training.id,
            'status': training.status,
            'is_active': training.is_active(),
            'settings': training.settings,
            'results': training.results,
            'notes': training.notes,
            'created_at': training.created_at,
            'updated_at': training.updated_at
        }
    })

##
## Project APIs (list, train and generate inferences on models)
##

@api_view(['GET', 'POST'])
def handle_prj(request: Request, project_id: str) -> Response:
    """ Returns project settings for the given project_id """
    logger.info('handle_prj - project_id: %s', project_id)
    project, _ = get_project_model(project_id)
    return project_response(project)


@api_view(['GET', 'POST'])
def handle_prj_training(request: Request, project_id: str) -> Response:
    """ Create training request for given project """
    try:
        api_check_authorization(request, project_id)
        project = api.models.Project.objects.get(pk=project_id)
        training = api.models.Training()

        training.project = project
        training.settings = project.settings
        training.settings['request'] = get_request_data_and_query(request) # settings overrides
        training.save()

        logger.info('handle_prj_training - project_id: %s, training_id: %s', project.id, training.id)
        return training_response(training)

    except ObjectDoesNotExist:
        raise NotFound('Project ' + project_id + ' could not be found')


@api_view(['GET', 'POST'])
def handle_prj_inference(request: Request, project_id: str) -> Response:
    """ Run inference on a given project id using its active trained model """
    logger.info('handle_prj_inference - project_id: %s', project_id)
    started_on = time_ms()
    api_check_authorization(request, project_id)

    # retrieve project, model and active training session
    project, model = get_project_model(project_id)
    training = api.models.Training.objects.get(pk=project.training_id) if project.training_id else None

    if not project.training_id:
        raise NotFound('Project ' + project_id + ' has not been trained yet.')

    model.settings = training.settings
    model.training = training.results

    request_data = api_get_parameter(request, 'data')
    if request_data is None:
        raise ParseError("API call should include 'data' field (see documentation).")

    results = model.predict(request_data)
    results['meta']['total_ms'] = time_ms(started_on)

    api.utilities.api_save_call(request, results)
    return Response(results)


@api_view(['PUT'])
def handle_prj_upload(request: Request, project_id:str, path: str) -> Response:
    """ Uploads an asset related to a project or gets upload keys to upload directly to google storage """
    logger.info('handle_prj_upload - project_id: %s, path: %s', project_id, path)
    api_check_authorization(request, project_id)
    name, ext = os.path.splitext(path)
    blobname = 'uploads/' + project_id + '/' + slugify(name) + '.' + slugify(ext)
    response = analitico.storage.upload_authorization(blobname)
    return Response(response)

##
## Training APIs (list, activate)
##

@api_view(['GET'])
def handle_trn(request: Request, training_id: str) -> Response:
    """ Return specified training record """
    try:
        logger.info('handle_trn - %s', training_id)
        training = api.models.Training.objects.get(pk=training_id)
        return training_response(training)
    except ObjectDoesNotExist:
        raise NotFound('Training ' + training_id + ' was not found')


@api_view(['GET'])
def handle_trn_activate(request: Request, training_id: str) -> Response:
    """ Activate training and return it """
    try:
        logger.info('handle_trn_activate - %s', training_id)
        training = api.models.Training.objects.get(pk=training_id)
        training.activate()
        return training_response(training)
    except ObjectDoesNotExist:
        raise NotFound('Training ' + training_id + ' was not found')

##
## Data uploads
##

