import simplejson as json
import stripe

import analitico.utilities
import api.utilities
import api.models

from analitico import AnaliticoException, logger
from api.notifications.slack import slack_send_internal_notification
from api.models import User, Workspace

# Stripe API:
# https://stripe.com/docs/api
# Stripe.js reference:
# https://stripe.com/docs/stripe-js/reference

# Checkout settings:
# https://dashboard.stripe.com/account/checkout/settings
# Checkout fullfillment:
# https://stripe.com/docs/payments/checkout/fulfillment
# Subscriptions APIs
# https://stripe.com/docs/api/subscriptions?lang=python

# pylint: disable=no-member

##
## Stripe methods and utilities
##


def stripe_to_dict(obj):
    """ Converts a stripe object to a regular dictionary. """
    return json.loads(str(obj))


def stripe_update_subscription(workspace: Workspace, subscription):
    """ Copy updated information from the subscription into the workspace. """
    stripe_conf = workspace.get_attribute("stripe", {})
    stripe_conf["customer_id"] = subscription.customer
    stripe_conf["subscription_id"] = subscription.id
    stripe_conf["subscription"] = {
        "id": subscription.id,
        "status": subscription.status,
        "livemode": subscription.livemode,
        "billing": subscription.billing,
        "created": subscription.created,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "customer": subscription.customer,
        "metadata": dict(subscription.metadata),
        "object": subscription.object,
        "plan": {"object": subscription.plan.object, "id": subscription.plan.id, "product": subscription.plan.product},
    }
    workspace.set_attribute("stripe", stripe_conf)
    workspace.save()


def stripe_get_plans():
    """ Retrieve list of currently active billing plans. """
    plans = stripe.Plan.list(active=True)
    return plans


def stripe_get_invoices(workspace: Workspace):
    """ Returns a list of invoices that were generated for the owner of the given workspace subscription (or None). """
    customer_id = workspace.get_attribute("stripe.customer_id", None)
    if not customer_id:
        return None
    # TODO could also retrieve all invoices then filter by metadata->workspace_id
    invoices = stripe.Invoice.list(customer=customer_id)
    return invoices


def stripe_get_subscription(workspace: Workspace):
    """ Returns the current Subscription for the given Workspace (or None). """
    subscription_id = workspace.get_attribute("stripe.subscription_id", None)
    return stripe.Subscription.retrieve(subscription_id) if subscription_id else None


def stripe_customer_retrieve(user: User, create: bool = True):
    """ Creates or retrieves existing stripe customer mapped to analitico user. """
    stripe_conf = user.get_attribute("stripe", {})
    if "customer_id" in stripe_conf:
        return stripe.Customer.retrieve(stripe_conf["customer_id"])

    if not create:
        raise AnaliticoException(f"User {user.email} does not have a stripe customer record.")

    customer = None
    customers = stripe.Customer.list(limit=1, email=user.email)
    if customers.data:
        customer = customers.data[0]
    else:
        customer = stripe.Customer.create(email=user.email)

    # store in user for later use
    stripe_conf["customer_id"] = customer.id
    user.set_attribute("stripe", stripe_conf)
    user.save()
    return customer


def stripe_session_create(user: api.models.User, workspace: api.models.Workspace = None, plan: str = None):
    """
    Creates a checkout session that can be used to purchase a subscription plan.
    
    Arguments:
        user {User} -- The authenticated user that we are purchasing this plan for.
        workspace {Workspace} -- The workspace we are purchasing the plan for (None if the workspace will be created).
        plan {str} -- The plan to be purchased, eg: plan_premium_usd

    Returns:
        [dict] -- Summary information on the session that was created.
    """

    # retrieve stripe user and create if needed
    customer = stripe_customer_retrieve(user)

    # subscription can be for an existing workspace or one that will be created with a new id
    workspace_id = workspace.id if workspace else api.models.workspace.generate_workspace_id()

    # Create a session:
    # https://stripe.com/docs/api/checkout/sessions/create
    # https://stripe.com/docs/stripe-js/reference#stripe-redirect-to-checkout
    session = stripe.checkout.Session.create(
        customer=customer.id,
        payment_method_types=["card"],
        billing_address_collection="required",
        success_url="https://staging.analitico.ai/workspaces?checkout=success",
        cancel_url="https://staging.analitico.ai/workspaces?checkout=cancel",
        subscription_data={
            "trial_period_days": 14,
            "items": [{"plan": plan, "quantity": 1}],
            "metadata": {"workspace_id": workspace_id},
        },
    )
    return session


##
## Webhook and events
##


# Example of events flow to create a subscription:
#
# customer.created (test)
# https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9YpEy8r6Pg
#
# payment_method.attached (test)
# https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9YtLLsxJET
#
# setup_intent.created (test)
# https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9Yvi0UeKp6
#
# setup_intent.succeeded (test)
# https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9YJo1S2AJE
#
# invoice.created (test)
# https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9YFu6SBngY
#
# customer.updated (test)
# https://dashboard.stripe.com/test/events/evt_1F44YxAICbSiYX9YRqEfkouH
#
# customer.subscription.created (test)
# https://dashboard.stripe.com/test/events/evt_1F44YxAICbSiYX9YTzuuGI1y
#
# invoice.finalized (test)
# https://dashboard.stripe.com/test/events/evt_1F44YxAICbSiYX9Y2dMecaKj
#
# invoice.updated (test)
# https://dashboard.stripe.com/test/events/evt_1F44YxAICbSiYX9Ye9fON4Uw
#
# invoice.payment_succeeded (test)
# https://dashboard.stripe.com/test/events/evt_1F44YyAICbSiYX9YNAuSTXjT
#
# checkout.session.completed (test)
# https://dashboard.stripe.com/test/events/evt_1F44YyAICbSiYX9YdqLcjLoA


def stripe_handle_checkout_customer_created(event):
    """ When a customer is created in stripe, add its customer_id in analitico. """
    customer = event.data.object
    email = customer.email

    user = User.objects.get(email=email)
    stripe = user.get_attribute("stripe", {})
    stripe["customer_id"] = customer.id
    user.set_attribute("stripe", stripe)
    user.save()


def stripe_handle_customer_subscription_created(event):
    """ A subscription has been created for an existing workspace or a new workspace to be provisioned. """
    subscription = event.data.object

    workspace_id = subscription.metadata.get("workspace_id")
    if not workspace_id:
        workspace_id = api.models.workspace.generate_workspace_id()
    try:
        # assign the new or renewed subscription to an existing workspace
        workspace = Workspace.objects.get(pk=workspace_id)
    except Workspace.DoesNotExist:
        # create a new workspace using the workspace_id that was indicated in metadata
        workspace = Workspace(id=workspace_id)

    stripe_update_subscription(workspace, subscription)
    workspace.save()


def stripe_handle_event(event_id: str):
    """
    Handle an event received from stripe. We only pass the event id.
    The actual event contents are retrieved directly from Stripe.
    
    Arguments:
        event_id {str} -- The event id.
    """
    try:
        # The event we receive from Stripe is signed and contains enough information
        # so that it's source can be verified. However, it is quite complicated to simulate
        # these flows for unit testing and also taking information directly from the event
        # itself is not suggested. So we do the safer thing and just take the event id from
        # the event itself then ask Stripe for the information so we're 100% sure it's real.
        event = stripe.Event.retrieve(event_id)

        # handle different kinds of stripe events
        if event.type == "customer.created":
            stripe_handle_checkout_customer_created(event)
        elif event.type == "customer.subscription.created":
            stripe_handle_customer_subscription_created(event)

    except Exception as exc:
        logger.error(f"stripe_handle_event - error while handling {event_id}, exc: {exc}")
        raise exc
