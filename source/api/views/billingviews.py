
import simplejson as json

from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.decorators import action, api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from rest_framework.authentication import SessionAuthentication, BasicAuthentication

import analitico.utilities
from api.views.k8viewsetmixin import get_namespace, get_kubctl_response, K8ViewSetMixin
import api.utilities

from analitico import AnaliticoException, logger
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt

class BillingViewSet(ViewSet):
    """ APIs to enable subscriptions, payments, etc. """

    # Defined in subclass, eg: api.models.Endpoint
    item_class = None

    # Defined in subclass, eg: EndpointSerializer
    serializer_class = None

    # All methods require prior authentication, no token, no access
    permission_classes = (AllowAny,)

    # Default format for requests is json
    format_kwarg = "json"

    authentication_classes = []# [SessionAuthentication, BasicAuthentication]
    #permission_classes = [IsAuthenticated]


    ##
    ## Cluster information (these APIs do not require an item_id)
    ##

    # WTF? not taking aunauthenticated calls
    @csrf_exempt
    @action(methods=["get, post"], detail=False, url_name="stripe-webhook", url_path="stripe/webhook", permission_classes=None)
    def stripe_webook(self, request):
        """ Stripe will call us on this endpoint with events related to billing, sales, subscriptions, etc... """
        
        event = request.data
        event_type = event["type"]

        send_mail(
                subject=f"Stripe webhook: {event_type}",
                message=json.dumps(event, indent=4),
                from_email="notifications@analitico.ai",
                recipient_list=["gionata.mettifogo@analitico.ai"],
                fail_silently=False,
            )

        return Response(status=status.HTTP_200_OK)


# Checkout settings:
# https://dashboard.stripe.com/account/checkout/settings

# Checkout fullfillment:
# https://stripe.com/docs/payments/checkout/fulfillment

# Subscriptions APIs
# https://stripe.com/docs/api/subscriptions?lang=python

@api_view(['GET', 'POST'])
def stripe_webhook(request: Request) -> Response:

    event = request.data["data"]
    event_type = event["type"]
    event_json = json.dumps(event, indent=4)
    logger.info(f"stripe_webhook - {event_type}\n\n{event_json}")

    send_mail(
        subject=f"Stripe webhook: {event_type}",
        message=json.dumps(event, indent=4),
        from_email="notifications@analitico.ai",
        recipient_list=["gionata.mettifogo@analitico.ai"],
        fail_silently=False,
    )

    return Response(status=status.HTTP_200_OK)