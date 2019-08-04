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


class BillingViewSetMixin:
    """ 
    APIs to enable subscriptions, payments, etc. 
    The billing flow is implemented via Stripe Checkout and Billing APIs.

    Checkout settings:
    https://dashboard.stripe.com/account/checkout/settings

    Checkout fullfillment:
    https://stripe.com/docs/payments/checkout/fulfillment

    Subscriptions APIs
    https://stripe.com/docs/api/subscriptions?lang=python
    
    """

    @csrf_exempt
    @action(
        methods=["get", "post"],
        detail=False,
        url_name="billing-stripe-webhook",
        url_path="billing/stripe/webhook",
        permission_classes=(AllowAny,),
    )
    def stripe_webook(self, request):
        """ Stripe will call us on this endpoint with events related to billing, sales, subscriptions, etc... """
        try:
            event = request.data["data"]
            reply = stripe_process_event(event)
        except Exception as exc:
            logger.error(f"stripe_webook - error while processing: {request.data}")
            raise exc
        return Response(reply, status=status.HTTP_200_OK)

##
## Stripe utilities
##

def stripe_process_event(event: dict) -> dict:

    event_type = event["type"]
    event_livemode = event.get("livemode", False)

    event_subject = f"Stripe: {event_type} {'' if event_livemode else ' (test)'}"
    event_message = json.dumps(event, indent=4)
    send_mail(
        subject=event_subject,
        message=event_message,
        from_email="notifications@analitico.ai",
        recipient_list=["gionata.mettifogo@analitico.ai"],
        fail_silently=False,
    )

    return {}
