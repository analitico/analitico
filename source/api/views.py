
import copy

from django.shortcuts import render

from rest_framework import routers, serializers, viewsets
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, APIException, ParseError

import analitico.models
import analitico.utilities

import api.utilities

import s24.ordertime
import s24.ordersorting


from analitico.models import AnaliticoModel, TabularRegressorModel

from api.models import User, Project, Training
from api.utilities import api_wrapper, api_handle_inference, time_ms, api_get_parameter, api_check_authorization

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
def handle_prj(request: Request, project_id: str) -> Response:
    """ Returns project settings for the given project_id """
    project, _ = get_project_model(project_id)
    return Response({ 'data': { 'settings': project.settings }})



@api_view(['GET', 'POST'])
def handle_prj_training(request: Request, project_id: str) -> Response:
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
def handle_prj_inference(request: Request, project_id: str) -> Response:
    """ Run inference on a given project id using its active trained model """
    started_on = time_ms()
    api_check_authorization(request, project_id)

    # retrieve project, model and active training session
    project, model = get_project_model(project_id)
    training = Training.objects.get(pk=project.training_id) if project.training_id else None

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


