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

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

# TODO fix styles, logos, etc
# https://www.django-rest-framework.org/topics/browsable-api/


# https://www.django-rest-framework.org/topics/documenting-your-api/
# https://www.django-rest-framework.org/api-guide/viewsets/


##
## Utility methods
##


def get_request_data_and_query(request):
    data = request.data.copy()
    for key, value in request.GET.items():
        data[key] = value if len(value) != 1 else value[0]
    return data


def training_response(training):
    """ Return an API Response containing the given Training """
    return Response(
        {
            "data": {
                "project_id": training.project.id,
                "training_id": training.id,
                "status": training.status,
                "is_active": training.is_active(),
                "settings": training.settings,
                "results": training.results,
                "notes": training.notes,
                "created_at": training.created_at,
                "updated_at": training.updated_at,
            }
        }
    )


##
## Project APIs (list, train and generate inferences on models)
##


@api_view(["GET", "POST"])
def handle_prj_training(request: Request, project_id: str) -> Response:
    """ Create training request for given project """
    try:
        api_check_authorization(request, project_id)
        project = api.models.Project.objects.get(pk=project_id)
        training = api.models.Training()

        training.project = project
        training.settings = project.settings
        training.settings["request"] = get_request_data_and_query(request)  # settings overrides
        training.save()

        logger.info("handle_prj_training - project_id: %s, training_id: %s", project.id, training.id)
        return training_response(training)

    except ObjectDoesNotExist:
        raise NotFound("Project " + project_id + " could not be found")


@api_view(["PUT"])
def handle_prj_upload(request: Request, project_id: str, path: str) -> Response:
    """ Uploads an asset related to a project or gets upload keys to upload directly to google storage """
    logger.info("handle_prj_upload - project_id: %s, path: %s", project_id, path)
    api_check_authorization(request, project_id)
    name, ext = os.path.splitext(path)
    blobname = "uploads/" + project_id + "/" + slugify(name) + "." + slugify(ext)
    response = analitico.storage.upload_authorization(blobname)
    return Response(response)


##
## Training APIs (list, activate)
##


@api_view(["GET"])
def handle_trn(request: Request, training_id: str) -> Response:
    """ Return specified training record """
    try:
        logger.info("handle_trn - %s", training_id)
        training = api.models.Training.objects.get(pk=training_id)
        return training_response(training)
    except ObjectDoesNotExist:
        raise NotFound("Training " + training_id + " was not found")


@api_view(["GET"])
def handle_trn_activate(request: Request, training_id: str) -> Response:
    """ Activate training and return it """
    try:
        logger.info("handle_trn_activate - %s", training_id)
        training = api.models.Training.objects.get(pk=training_id)
        training.activate()
        return training_response(training)
    except ObjectDoesNotExist:
        raise NotFound("Training " + training_id + " was not found")
