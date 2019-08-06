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

    def test_billing_plans(self):
        # Retrieve list of active billing plans
        # GET /api/workspaces/billing/plans
        self.auth_token(None)  # no auth
        url = reverse("api:billing-plans")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        for plan in data:
            self.assertEqual(plan["type"], "analitico/stripe-plan")
            self.assertIn("id", plan)
            self.assertTrue(plan["attributes"]["active"])
            self.assertIn(plan["attributes"]["currency"], ("usd", "eur"))

    def test_billing_session_create(self):
        self.auth_token(self.token3)  # regular user
        url = reverse("api:billing-session") + "?plan=plan_premium_usd"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        self.assertEqual(data["attributes"]["livemode"], False)
        self.assertEqual(data["attributes"]["customer"], "cus_FZH0mmWGNI2K9G")

    def test_billing_session_create_no_auth(self):
        self.auth_token(None)  # no authentication
        url = reverse("api:billing-session") + "?plan=plan_premium_usd"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
        url = reverse("api:billing-webhook")
        response = self.client.post(url, event, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = api.models.User.objects.get(email="user1@analitico.ai")
        stripe = user.get_attribute("stripe")
        self.assertEqual(stripe["customer_id"], "cus_FYvVlgYdX79DVl")

    def test_billing_stripe_webhook_customer_subscription_created(self):
        # customer.subscription.created -> workspace created and configured
        event = {
            "id": "evt_1F48cAAICbSiYX9YRsYN7YaO",
            "object": "event",
            "type": "customer.subscription.created",
            "api_version": "2019-05-16",
            "created": 1565020849,
            "data": None,
            "livemode": False,
        }
        url = reverse("api:billing-webhook")
        response = self.client.post(url, event, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        workspace = api.models.Workspace.objects.get(pk="ws_e78c8o4y")
        stripe_conf = workspace.get_attribute("stripe")

        self.assertEqual(stripe_conf["customer_id"], "cus_FZH0mmWGNI2K9G")
        self.assertEqual(stripe_conf["subscription_id"], "sub_FZHAgRNxpptZ2Y")

        # Retrieve subscription on this workspace
        # GET /api/billing/ws_xxx/subscription
        self.auth_token(self.token1)  # user1
        url = reverse("api:billing-subscription", args=(workspace.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["type"], "analitico/stripe-subscription")
        self.assertEqual(data["attributes"]["object"], "subscription")
        self.assertEqual(data["attributes"]["plan"]["object"], "plan")

        # Retrieve list of invoices generated for a given workspace
        # GET /api/workspaces/billing/plans
        self.auth_token(self.token1)  # user1
        url = reverse("api:billing-invoices", args=(workspace.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        for invoice in data:
            self.assertEqual(invoice["type"], "analitico/stripe-invoice")
            self.assertIn("id", invoice)

    def test_billing_stripe_get_invoices_no_invoices(self):
        # Retrieve list of invoices generated for a given workspace when the workspace has no stripe configuration
        self.auth_token(self.token1)  # user1
        url = reverse("api:billing-invoices", args=(self.ws1.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
