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

        event = request.data["data"]
        event_type = event["type"]

        send_mail(
            subject=f"Stripe webhook: {event_type}",
            message=json.dumps(event, indent=4),
            from_email="notifications@analitico.ai",
            recipient_list=["gionata.mettifogo@analitico.ai"],
            fail_silently=False,
        )

        return Response(status=status.HTTP_200_OK)

