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

CUSTOMER_EVENTS = ("customer.created", "customer.updated")

SUBSCRIPTION_EVENTS = (
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
)


##
## Stripe methods and utilities
##


def stripe_to_dict(obj):
    """ Converts a stripe object to a regular dictionary. """
    return json.loads(str(obj))


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


def stripe_cancel_subscription(workspace: Workspace):
    """ Cancels the workspace subscription and returns it (or None). """
    subscription_id = workspace.get_attribute("stripe.subscription_id", None)
    return stripe.Subscription.delete(subscription_id) if subscription_id else None


def stripe_change_subscription_plan(workspace: Workspace, plan_id: str):
    """ Changes the subscription to the given plan. """
    subscription_id = workspace.get_attribute("stripe.subscription_id", None)
    if not subscription_id:
        raise AnaliticoException(
            f"stripe_change_subscription_plan - {workspace.id} does not have an active subscription."
        )
    subscription = stripe.Subscription.retrieve(subscription_id)
    subscription = stripe.Subscription.modify(
        subscription.id,
        cancel_at_period_end=False,
        items=[{"id": subscription["items"]["data"][0].id, "plan": plan_id}],
    )
    return subscription


def stripe_get_customer(user: User, create: bool = True):
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
    customer = stripe_get_customer(user)
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


def stripe_handle_customer_event(event):
    """ When a customer is created in stripe, add its customer_id in analitico. """
    customer = event.data.object
    email = customer.email
    user = User.objects.get(email=email)

    stripe_conf = user.get_attribute("stripe", {})
    stripe_conf["customer_id"] = customer.id
    stripe_conf["customer"] = stripe_to_dict(customer)

    user.set_attribute("stripe", stripe_conf)
    user.save()
    return True


def stripe_handle_subscription_event(event):
    """ A subscription has been created for an existing workspace or a new workspace to be provisioned. """
    assert event.type in SUBSCRIPTION_EVENTS
    subscription = event.data.object
    workspace_id = subscription.metadata.get("workspace_id")
    if not workspace_id:
        msg = f"A {event.id} event was received but the subscription metadata is missing a workspace_id field."
        raise AnaliticoException(msg)

    try:
        # assign the new or updated subscription to an existing workspace
        workspace = Workspace.objects.get(pk=workspace_id)
    except Workspace.DoesNotExist as exc:
        if event.type != "customer.subscription.created":
            msg = f"A {event.id} event was received but the {workspace_id} cannot be found."
            raise AnaliticoException(msg) from exc
        # create a new workspace using the workspace_id that was indicated in metadata
        workspace = Workspace(id=workspace_id)

    stripe_conf = workspace.get_attribute("stripe", {})
    stripe_conf["customer_id"] = subscription.customer
    stripe_conf["subscription_id"] = subscription.id
    stripe_conf["subscription"] = stripe_to_dict(subscription)

    workspace.set_attribute("stripe", stripe_conf)
    workspace.save()
    return True


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
        if event.type in CUSTOMER_EVENTS:
            return stripe_handle_customer_event(event)
        elif event.type in SUBSCRIPTION_EVENTS:
            return stripe_handle_subscription_event(event)
        return False

    except Exception as exc:
        logger.error(f"stripe_handle_event - error while handling {event_id}, exc: {exc}")
        raise exc
