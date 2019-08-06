from django.conf import settings

from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

import analitico.utilities
import api.billing
import api.utilities

from analitico import AnaliticoException, logger
from api.notifications.slack import slack_send_internal_notification
from api.factory import factory
from api.permissions import HasApiPermission, has_item_permission_or_exception


class BillingViewSet(ViewSet):
    """ Analitico billing views implemented with Stripe Checkout, Stripe Billing and custom logic. """

    # All methods require prior authentication, no token, no access except when explicitely specified
    permission_classes = (IsAuthenticated, HasApiPermission)

    @action(methods=["get"], detail=False, url_name="plans", url_path="plans", permission_classes=(AllowAny,))
    def billing_plans(self, request: Request):
        """ Returns a list of available plans that users can choose from. """
        plans = api.billing.stripe_get_plans()
        plans_reply = [
            {"type": "analitico/stripe-plan", "id": plan.id, "attributes": api.billing.stripe_to_dict(plan)}
            for plan in plans
        ]
        return Response(plans_reply, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=False, url_name="session", url_path="session")
    def billing_session(self, request: Request):
        """ Create a checkout session that can be used by current user to purchase a subscription plan for a new workspace. """
        plan = api.utilities.get_query_parameter(request, "plan")
        if not plan:
            raise AnaliticoException(
                "Please provide ?plan= to be purchased with checkout.", status_code=status.HTTP_400_BAD_REQUEST
            )
        session = api.billing.stripe_session_create(request.user, workspace=None, plan=plan)
        session_reply = {
            "type": "analitico/stripe-session",
            "id": session.id,
            "attributes": api.billing.stripe_to_dict(session),
        }
        return Response(session_reply, status=status.HTTP_201_CREATED)

    @action(methods=["get"], detail=True, url_name="invoices", url_path="invoices")
    def billing_invoices(self, request: Request, pk: str):
        """ Returns a list of invoices that have been generated for a specific workspace. """
        workspace = factory.get_item(pk)
        has_item_permission_or_exception(request.user, workspace, "analitico.workspaces.get")

        invoices = api.billing.stripe_get_invoices(workspace)
        if invoices:
            invoices_reply = [
                {
                    "type": "analitico/stripe-invoice",
                    "id": invoice.id,
                    "attributes": api.billing.stripe_to_dict(invoice),
                }
                for invoice in invoices
            ]
            return Response(invoices_reply, status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=True, url_name="subscription", url_path="subscription")
    def billing_subscription(self, request: Request, pk: str):
        """ Returns the current subscription on the given workspace. """
        workspace = factory.get_item(pk)
        has_item_permission_or_exception(request.user, workspace, "analitico.workspaces.get")
        subscription = api.billing.stripe_get_subscription(workspace)
        if subscription:
            subscription_reply = {
                "type": "analitico/stripe-subscription",
                "id": subscription.id,
                "attributes": api.billing.stripe_to_dict(subscription),
            }
            return Response(subscription_reply, status=status.HTTP_200_OK)
        return Response([], status=status.HTTP_204_NO_CONTENT)

    @action(methods=["post"], detail=False, url_name="webhook", url_path="webhook", permission_classes=(AllowAny,))
    def billing_webook(self, request: Request):
        """ Stripe webhook used to receive billing events. """
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
