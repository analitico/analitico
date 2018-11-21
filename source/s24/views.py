
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view
from analitico.api import api_wrapper

import s24.ordersorting
import s24.ordertime

# cached model used to predict order times
ordertime_model = None

@api_view(['GET', 'POST'])
def order_sorting(request: Request) -> Response:
    return api_wrapper(s24.ordersorting.handle_request, request)

@api_view(['GET', 'POST'])
def order_time(request: Request) -> Response:
    global ordertime_model
    if (ordertime_model is None):
        ordertime_model = s24.ordertime.OrderTimeModel()
    return api_wrapper(ordertime_model.predict_request, request)
