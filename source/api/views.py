
import copy

from django.shortcuts import render

from rest_framework import routers, serializers, viewsets
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound

import analitico.models
import s24.ordertime
import s24.ordersorting

import analitico.utilities

from analitico.models import AnaliticoModel, TabularRegressorModel

from api.models import User, Project, Training
from api.utilities import api_wrapper, api_handle_inference

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

# TODO fix styles, logos, etc
# https://www.django-rest-framework.org/topics/browsable-api/


MODELS = {
    # generic regressor from tabular data
    'tabular-regressor-model': analitico.models.TabularRegressorModel,

    # model to estimate s24 order time    
    's24-order-time-model': s24.ordertime.OrderTimeModel,

    # model to sort s24 orders based on supermarket layout    
    's24-order-sorting-model': s24.ordersorting.handle_request,
}


# Serializers define the API representation.
#class UserSerializer(serializers.HyperlinkedModelSerializer):
#    class Meta:
#        model = User2
#        fields = ('url', 'username', 'email', 'is_staff')

# ViewSets define the view behavior.
#class UserViewSet(viewsets.ModelViewSet):
#    queryset = User.objects.all()
#    serializer_class = UserSerializer

##
## supermercato24.it
##

import s24.ordersorting
import s24.ordertime

# cached model used to predict order times
ordertime_model = None

@api_view(['GET', 'POST'])
def s24_order_sorting(request: Request) -> Response:
    return api_wrapper(s24.ordersorting.handle_request, request)

@api_view(['GET', 'POST'])
def s24_order_time(request: Request) -> Response:
    global ordertime_model
    if (ordertime_model is None):
        ordertime_model = s24.ordertime.OrderTimeModel()
    return  api_handle_inference(ordertime_model, request)


#
# APIs to list, train and generate inferences on models
#

def get_project_model(project_id: str) -> (Project, AnaliticoModel):
    """ Returns an initialized model for the given project """
    try:
        project = Project.objects.get(pk=project_id)
        settings = project.settings
        # TODO check access permissions
        try:
            return project, MODELS[settings['model_id']](settings)
        except:
            pass
        return project, MODELS[project_id + '-model'](settings)
    except:
        raise NotFound('Model for ' + project_id + ' was not found')



@api_view(['GET', 'POST'])
def handle_project(request: Request, project_id: str) -> Response:
    """ Returns project settings for the given project_id """
    project, _ = get_project_model(project_id)
    return Response({ 'data': { 'settings': project.settings }})



@api_view(['GET', 'POST'])
def handle_training(request: Request, project_id: str) -> Response:
    """ Train project with given data, return training results """
    training = Training()
    project, model = get_project_model(project_id)

    # if training data was passed, replace predefined settings
    if request.data:
        model.settings = copy.deepcopy(model.settings)
        model.settings['training_data'] = request.data

    training.project = project
    training.settings = model.settings
    training.save()

    results = model.train(training.id)
    training.results = results
    training.save()

    return Response(results)



@api_view(['GET', 'POST'])
def handle_inference(request: Request, project_id: str) -> Response:
    project, model = get_project_model(project_id)
    return Response('Inference: ' + project_id)


