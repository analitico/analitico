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
        try:
            reply = stripe_process_event(request)
        except Exception as exc:
            logger.error(f"stripe_webook - error while processing: {request.data}")
            raise exc
        return Response(reply, status=status.HTTP_200_OK)

##
## Stripe utilities
##


# These are test tokens, actual tokens are in secrets
ANALITICO_STRIPE_SECRET_KEY = "sk_test_HOYuiExkdXkVdrhov3M6LwQQ"
ANALITICO_STRIPE_ENDPOINT_SECRET = "whsec_6N2uPjVqWBB99TNRj9HQ5UwRWRNSvl9G"

stripe.api_key = ANALITICO_STRIPE_SECRET_KEY

def stripe_handle_checkout_session_completed(request: Request, session):
    pass

def stripe_process_event(request: Request) -> dict:

    event_payload = request.body
    event_data = json.loads(event_payload.decode())
    event_type = event_data["type"]
    event_livemode = event_data.get("livemode", False)

    event_subject = f"Stripe: {event_type} {'' if event_livemode else ' (test)'}"
    event_message = json.dumps(event_data, indent=4)
    send_mail(
        subject=event_subject,
        message=event_message,
        from_email="notifications@analitico.ai",
        recipient_list=["gionata.mettifogo@analitico.ai"],
        fail_silently=False,
    )

    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    # turn into actual stripe event
    try:
        event = stripe.Webhook.construct_event(event_payload, sig_header, ANALITICO_STRIPE_ENDPOINT_SECRET)
    except ValueError as exc:
        raise AnaliticoException("stripe_process_event - invalid payload", status_code=status.HTTP_400_BAD_REQUEST) from exc
    except stripe.error.SignatureVerificationError as exc:
        raise AnaliticoException("stripe_process_event - invalid signature", status_code=status.HTTP_400_BAD_REQUEST) from exc

    # handle different kinds of stripe events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        stripe_handle_checkout_session_completed(request, session)

    return {}
