import simplejson as json

from collections import OrderedDict
from django.conf import settings
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.decorators import action, api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from rest_framework.authentication import SessionAuthentication, BasicAuthentication

import analitico.utilities
from api.notifications.slack import slack_send_internal_notification

import api.billing
import api.utilities

from analitico import AnaliticoException, logger
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt

import stripe


class BillingViewSetMixin:
    """ Analitico billing views implemented with Stripe Checkout, Stripe Billing and custom logic. """

    @action(
        methods=["get"],
        detail=False,
        url_name="billing-plans",
        url_path="billing/plans",
        permission_classes=(AllowAny,),
    )
    def billing_plans(self, request):
        """ Returns a list of available plans that users can choose from. """
        plans = api.billing.stripe_get_plans()
        plans_reply = [
            {"type": "analitico/stripe-plan", "id": plan.id, "attributes": api.billing.stripe_to_dict(plan)}
            for plan in plans.data
        ]
        return Response(plans_reply)

    @action(methods=["post"], detail=False, url_name="billing-session-create", url_path="billing/session")
    def billing_session_create(self, request):
        """ Create a checkout session that can be used by current user to purchase a subscription plan for a new workspace. """
        plan = api.utilities.get_query_parameter(request, "plan")
        if not plan:
            raise AnaliticoException(
                "Please provide ?plan= to be purchased with checkout.", status_code=status.HTTP_400_BAD_REQUEST
            )

        # create a checkout session where I can purchase a subscription plan for a new workspace to be created
        session = api.billing.stripe_session_create(request.user, workspace=None, plan=plan)
        session_reply = {
            "type": "analitico/stripe-session",
            "id": session.id,
            "attributes": {
                "id": session.id,
                "object": session.object,
                "customer": session.customer,
                "livemode": session.livemode,
                "success_url": session.success_url,
                "cancel_url": session.cancel_url,
            },
        }
        return Response(session_reply, status=status.HTTP_201_CREATED)

    @csrf_exempt
    @action(
        methods=["get", "post"],
        detail=False,
        url_name="billing-webhook",
        url_path="billing/webhook",
        permission_classes=(AllowAny,),
    )
    def billing_webook(self, request):
        """ Stripe will call us on this endpoint with events related to billing, sales, subscriptions, etc... """
        color = "good"
        event_data = request.data
        event_type = event_data["type"]
        event_id = event_data["id"]
        event_livemode = event_data["livemode"]

        # production endpoints will not process test events and will return a differentiated
        # reply with a 204 status code so we can tell in stripe's backoffice that they weren't processed
        if event_livemode is False:
            if not settings.TESTING:
                return Response(status=status.HTTP_204_NO_CONTENT)

        try:
            api.billing.stripe_handle_event(event_id)

        except Exception as exc:
            logger.error(f"stripe_webook - error while processing: {request.data}")
            color = "danger"
            raise exc

        finally:
            # notification information for the received event is sent to internal slack channel
            subject = f"Stripe *{event_type}*{'' if event_livemode else ' (test)'}"
            message = f"https://dashboard.stripe.com/{'' if event_livemode else 'test/'}events/{event_id}"
            slack_send_internal_notification(subject, message, color, channel="stripe")

        return Response(status=status.HTTP_200_OK)
