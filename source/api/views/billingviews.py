from django.conf import settings

import rest_framework.status
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

    ##
    ## Utilities
    ##

    def get_stripe_item_response(self, items, item_type, many=False, status=status.HTTP_200_OK):
        if many:
            if items:
                items_reply = [
                    {"type": item_type, "id": item.id, "attributes": api.billing.stripe_to_dict(item)} for item in items
                ]
                return Response(items_reply, status=status)
            return Response([], status=rest_framework.status.HTTP_204_NO_CONTENT)
        else:
            if items:  # single
                reply = {"type": item_type, "id": items.id, "attributes": api.billing.stripe_to_dict(items)}
                return Response(reply, status=status)
        return Response(status=rest_framework.status.HTTP_204_NO_CONTENT)

    ##
    ## Actions
    ##

    @action(methods=["get"], detail=False, url_name="plans", url_path="plans", permission_classes=(AllowAny,))
    def get_plans(self, request: Request):
        """ Returns a list of available plans that users can choose from. """
        plans = api.billing.stripe_get_plans()
        return self.get_stripe_item_response(plans, "analitico/stripe-plan", many=True)

    @action(methods=["post"], detail=False, url_name="session", url_path="session")
    def create_session(self, request: Request):
        """ Create a checkout session that can be used by current user to purchase a subscription plan for a new workspace. """
        plan = api.utilities.get_query_parameter(request, "plan")
        if not plan:
            raise AnaliticoException(
                "Please provide ?plan= to be purchased with checkout.", status_code=status.HTTP_400_BAD_REQUEST
            )
        session = api.billing.stripe_session_create(request.user, workspace=None, plan=plan)
        return self.get_stripe_item_response(session, "analitico/stripe-session", status=status.HTTP_201_CREATED)

    @action(methods=["get"], detail=True, url_name="invoices", url_path="invoices")
    def get_invoices(self, request: Request, pk: str):
        """ Returns a list of invoices that have been generated for a specific workspace. """
        workspace = factory.get_item(pk)
        has_item_permission_or_exception(request.user, workspace, "analitico.workspaces.get")
        invoices = api.billing.stripe_get_invoices(workspace)
        return self.get_stripe_item_response(invoices, "analitico/stripe-invoice", many=True)

    @action(methods=["get"], detail=True, url_name="subscription", url_path="subscription")
    def get_subscription(self, request: Request, pk: str):
        """ Returns the current subscription on the given workspace. """
        workspace = factory.get_item(pk)
        has_item_permission_or_exception(request.user, workspace, "analitico.workspaces.get")
        subscription = api.billing.stripe_get_subscription(workspace)
        return self.get_stripe_item_response(subscription, "analitico/stripe-subscription")

    @action(
        methods=["post"],
        detail=True,
        url_name="subscription-plan-change",
        url_path=r"subscription/plan/(?P<plan_id>[-\w]+)",
    )
    def change_subscription_plan(self, request: Request, pk: str, plan_id: str):
        """ Cancels a workspace's subscription immediately. """
        # must own the workspace to be able to change its plan
        workspace = factory.get_item(pk)
        has_item_permission_or_exception(request.user, workspace, "analitico.workspaces.admin")
        subscription = api.billing.stripe_change_subscription_plan(workspace, plan_id)
        return self.get_stripe_item_response(
            subscription, "analitico/stripe-subscription", status=status.HTTP_201_CREATED
        )

    @action(methods=["post"], detail=True, url_name="subscription-cancel", url_path="subscription/cancel")
    def cancel_subscription(self, request: Request, pk: str):
        """ Cancels a workspace's subscription immediately. """
        workspace = factory.get_item(pk)
        has_item_permission_or_exception(
            request.user, workspace, "analitico.workspaces.admin"
        )  # must own the workspace
        subscription = api.billing.stripe_cancel_subscription(workspace)
        return self.get_stripe_item_response(subscription, "analitico/stripe-subscription")

    ##
    ## Stripe events webhook
    ##

    @action(methods=["post"], detail=False, url_name="webhook", url_path="webhook", permission_classes=(AllowAny,))
    def webook(self, request: Request):
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
