# ProjectSerializer and ProjectViewSet for project APIs
# pylint: disable=no-member

from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist

import rest_framework
from rest_framework import serializers
from rest_framework import exceptions

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ParseError

from api.models import Project
from analitico.utilities import logger
from api.utilities import time_ms, api_get_parameter, api_check_authorization

import analitico.models
import analitico.utilities
import analitico.storage
import api.models
import api.utilities
import s24.models

# Django Serializers
# https://www.django-rest-framework.org/api-guide/serializers/

# Django ViewSet
# https://www.django-rest-framework.org/api-guide/viewsets/

##
## Utility methods
##

MODELS = {
    # generic regressor from tabular data
    "tabular-regressor-model": analitico.models.TabularRegressorModel,
    # model to estimate s24 order time
    "s24-order-time-model": s24.models.OrderTimeModel,
    # model to sort s24 orders based on supermarket layout
    "s24-order-sorting-model": s24.models.OrderSortingModel,
    # model to predict if items may be out of stock
    "s24-out-of-stock-model": s24.models.OutOfStockModel,
}


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
            return project, MODELS[settings["model_id"]](settings)
        except Exception:
            pass
        return project, MODELS[project_id + "-model"](settings)
    except ObjectDoesNotExist:
        raise NotFound("Model for " + project_id + " was not found")


#
# Serializer
#


class ProjectSerializer(serializers.ModelSerializer):
    """ Serializer for machine learning projects. """

    class Meta:
        model = Project
        fields = ("id", "user", "group", "settings", "training_id", "notes", "created_at", "updated_at")

    id = serializers.SlugField(help_text=_("Unique id."))
    user = serializers.EmailField(source="owner.email", help_text=_("User that owns the project."), required=False)
    group = serializers.CharField(source="group.name", help_text=_("Project notes (markdown)"), required=False)

    settings = serializers.JSONField(
        help_text=_("Project settings including metadata, model type, training parameters, etc..."), required=False
    )
    training_id = serializers.SlugField(help_text=_("Training session currently used for inference."), required=False)
    notes = serializers.CharField(help_text=_("Project notes (markdown)"), required=False)

    created_at = serializers.DateTimeField(
        label=_("Created"), help_text=_("Date and time when project was created."), required=False
    )
    updated_at = serializers.DateTimeField(
        label=_("Updated"), help_text=_("Date and time when project was last updated."), required=False
    )


#
# ViewSet
#


class ProjectViewSet(rest_framework.viewsets.ModelViewSet):
    """ 
    List, detail, create, update and delete machine learning projects. 
    
    retrieve: Retrieve a specific project.
    list: Retrieve a list of projects for the user.
    create: Create a new project for the user.
    update: Update a previously created project.
    partial_update: Modify a previously created project.
    delete: Delete a project.
    """

    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    help_text = "help text viewset"
    label = "viewset label"

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            token = Project(pk=serializer.validated_data["id"])
            if "name" in serializer.validated_data:
                token.name = serializer.validated_data["name"]
            token.user = request.user
            token.save()
            serializer = ProjectSerializer(token)
            return Response(serializer.data, status=201)
        raise exceptions.ValidationError(serializer.errors)

    @action(detail=True, methods=["post"])
    def inference(self, request, pk=None):
        """ Run inference on a given project id using its active trained model """
        project_id = pk
        logger.info("ProjectViewSet.inference - project_id: %s", project_id)
        started_on = time_ms()
        api_check_authorization(request, project_id)

        # retrieve project, model and active training session
        project, model = get_project_model(project_id)
        if not project.training_id:
            raise NotFound("Project " + project_id + " has not been trained yet.")
        training = api.models.Training.objects.get(pk=project.training_id)

        model.settings = training.settings
        model.training = training.results

        request_data = api_get_parameter(request, "data")
        if request_data is None:
            raise ParseError("API call should include 'data' field (see documentation).")

        results = model.predict(request_data)
        results["meta"]["total_ms"] = time_ms(started_on)

        api.utilities.api_save_call(request, results)
        return Response(results)
