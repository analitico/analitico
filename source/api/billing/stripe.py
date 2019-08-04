import simplejson as json
import stripe

import analitico.utilities
import api.utilities
import api.models

from analitico import AnaliticoException, logger
from api.notifications.slack import slack_send_internal_notification
from api.models import User

# These are test tokens, actual tokens are in secrets
ANALITICO_STRIPE_SECRET_KEY = "sk_test_HOYuiExkdXkVdrhov3M6LwQQ"
ANALITICO_STRIPE_ENDPOINT_SECRET = "whsec_6N2uPjVqWBB99TNRj9HQ5UwRWRNSvl9G"

stripe.api_key = ANALITICO_STRIPE_SECRET_KEY


def stripe_handle_checkout_customer_created(event):
    """ When a customer is created in stripe, add its customer_id in analitico. """
    customer = event.data.object
    email = customer.email

    user = User.objects.get(email=email)
    stripe = user.get_attribute("stripe", {})
    stripe["customer_id"] = customer.id
    user.set_attribute("stripe", stripe)
    user.save()


def stripe_handle_checkout_session_completed(event):
    pass


def stripe_handle_event(event_id: str):
    try:
        # trust nobody, get the data from stripe
        event = stripe.Event.retrieve(event_id)

        # handle different kinds of stripe events
        if event.type == "customer.created":
            stripe_handle_checkout_customer_created(event)

    except Exception as exc:
        logger.error(f"stripe_handle_event - error while handling {event_id}, exc: {exc}")
        raise exc
