import simplejson as json

from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.decorators import action, api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from rest_framework.authentication import SessionAuthentication, BasicAuthentication

import analitico.utilities
from api.notifications.slack import slack_send_internal_notification
from api.billing.stripe import stripe_handle_event

import api.utilities

from analitico import AnaliticoException, logger
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt

import stripe


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
        color = "good"
        event_data = request.data
        event_type = event_data["type"]
        event_id = event_data["id"]
        event_livemode = event_data["livemode"]
        try:
            # The event we receive from Stripe is signed and contains enough information
            # so that it's source can be verified. However, it is quite complicated to simulate
            # these flows for unit testing and also taking information directly from the event
            # itself is not suggested. So we do the safer thing and just take the event id from
            # the event itself then ask Stripe for the information so we're 100% sure it's real.
            reply = stripe_handle_event(event_id)

        except Exception as exc:
            logger.error(f"stripe_webook - error while processing: {request.data}")
            color = "danger"
            raise exc

        finally:
            # notification information for the received event is sent to internal slack channel
            subject = f"Stripe *{event_type}*{'' if event_livemode else ' (test)'}"
            message = f"https://dashboard.stripe.com/{'' if event_livemode else 'test/'}events/{event_id}"
            slack_send_internal_notification(subject, message, color)

        return Response(reply, status=status.HTTP_200_OK)
