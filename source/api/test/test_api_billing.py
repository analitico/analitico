import os
import pytest
import stripe

from django.test import tag
from django.urls import reverse
from rest_framework import status

import analitico
import analitico.plugin
import api.models

from analitico import logger
from .utils import AnaliticoApiTestCase

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member
# pylint: disable=unused-variable


@pytest.mark.django_db
class BillingTests(AnaliticoApiTestCase):
    """ Test billing APIs and webhooks. """

    def setUp(self):
        self.setup_basics()

    def test_billing_stripe_webhook_customer_created(self):
        # this is not a full stripe event. we just have the basics
        # here since our code does not take the transaction info from
        # the event but just the id and gets the rest directly from Stripe
        event = {
            "id": "evt_1F3netAICbSiYX9Y0tvMj1IU",  # creates user1@analitico.ai
            "object": "event",
            "api_version": "2019-05-16",
            "created": 1564937322,
            "data": {},
            "livemode": False,
            "type": "customer.created",
        }
        url = reverse("api:workspace-billing-stripe-webhook")
        response = self.client.post(url, event, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = api.models.User.objects.get(email="user1@analitico.ai")
        stripe = user.get_attribute("stripe")
        self.assertEqual(stripe["customer_id"], "cus_FYvVlgYdX79DVl")

    def test_stripe_charge(self):
        # test account can create charges
        charge = stripe.Charge.create(
            amount=999, currency="usd", source="tok_visa", receipt_email="jenny.rosen@example.com"
        )
        self.assertEqual(charge["object"], "charge")
