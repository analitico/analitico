import os
import pytest
import stripe
import tempfile
import requests

from django.test import tag
from django.urls import reverse
from rest_framework import status

import analitico
import analitico.plugin
import api.models

from analitico import logger
from api.models import Workspace, User
from .utils import AnaliticoApiTestCase
from .test_api_user import TEST_USER_WITH_PASSWORD, TYPE_PREFIX, USER_TYPE, TEST_USER_EMAIL, TEST_USER_PASSWORD

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member
# pylint: disable=unused-variable

TEST_BILLING_PLAN1_ID = "plan_essentials_usd"
TEST_BILLING_PLAN2_ID = "plan_standard_usd"


# test / billing / disabled due to timeout error calling api.stripe.com #476 
@tag("slow")
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
        self.assertEqual(data["attributes"]["customer"], "cus_FZbGgzNiXyKEYS")

    def test_billing_session_create_with_newly_signed_up_user(self):
        url = reverse("api:user-signup")
        response = self.client.post(url, TEST_USER_WITH_PASSWORD, format="json")  # NO AUTH TOKEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        logged_in = self.client.login(username=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        self.assertTrue(logged_in)

        url = reverse("api:billing-session") + "?plan=plan_premium_usd"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data["attributes"]["livemode"], False)
        self.assertEqual(data["attributes"]["customer"], "cus_FdHPAsGYQEbSKj")

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
        workspace = None
        try:
            # customer.subscription.created -> workspace created and configured
            event = {
                "id": "evt_1F87ftAICbSiYX9Yr0C64hz6",
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

            workspace = api.models.Workspace.objects.get(pk="ws_0z7vjfe2")
            self.assertEqual(workspace.user.email, "user1@analitico.ai")
            stripe_conf = workspace.get_attribute("stripe")

            self.assertEqual(stripe_conf["customer_id"], "cus_FYvVlgYdX79DVl")
            self.assertEqual(stripe_conf["subscription_id"], "sub_FdOSjEbGLRmolX")

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
            self.assertGreaterEqual(len(data), 1)
            for invoice in data:
                self.assertEqual(invoice["type"], "analitico/stripe-invoice")
                self.assertIn("id", invoice)
                with tempfile.NamedTemporaryFile(prefix="invoice_", suffix=".pdf") as f:
                    # checks that no authorization is needed
                    response = requests.get(invoice["attributes"]["invoice_pdf"])
                    f.write(response.content)
        finally:
            # workspace storage needs to be deleted
            if workspace:
                workspace.delete()

    def test_billing_stripe_get_invoices_no_invoices(self):
        # Retrieve list of invoices generated for a given workspace when the workspace has no stripe configuration
        self.auth_token(self.token1)  # user1
        url = reverse("api:billing-invoices", args=(self.ws1.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_billing_subscription_lifecycle(self):
        # setup a customer with a new workspace that has a billing plan
        # then retri
        subscription = None
        user = self.user1
        customer = api.billing.stripe_get_customer(user)
        workspace = Workspace(user=user)
        try:
            subscription = stripe.Subscription.create(
                customer=customer.id,
                trial_period_days=7,
                items=[{"plan": TEST_BILLING_PLAN1_ID, "quantity": 1}],
                metadata={"workspace_id": workspace.id, "email": user.email},
            )
            workspace.set_attribute("stripe", {"customer_id": customer.id, "subscription_id": subscription.id})
            workspace.save()

            # GET /api/billing/ws_xxx/subscription
            self.auth_token(self.token1)  # user1
            url = reverse("api:billing-subscription", args=(workspace.id,))
            response1 = self.client.get(url)
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
            data1 = response1.data
            self.assertEqual(data1["type"], "analitico/stripe-subscription")
            self.assertEqual(data1["attributes"]["object"], "subscription")
            self.assertEqual(data1["attributes"]["status"], "trialing")
            self.assertEqual(data1["attributes"]["plan"]["object"], "plan")
            self.assertEqual(data1["attributes"]["plan"]["id"], TEST_BILLING_PLAN1_ID)
            self.assertEqual(data1["attributes"]["metadata"]["workspace_id"], workspace.id)
            self.assertEqual(data1["attributes"]["metadata"]["email"], user.email)

            # GET /api/billing/ws_xxx/invoice
            url = reverse("api:billing-invoices", args=(workspace.id,))
            response2 = self.client.get(url)
            self.assertEqual(response2.status_code, status.HTTP_200_OK)
            data2 = response2.data

            # POST /api/billing/ws_xxx/subscription/plan/plan_id (change plan)
            url = reverse("api:billing-subscription-plan-change", args=(workspace.id, TEST_BILLING_PLAN2_ID))
            response3 = self.client.post(url)
            self.assertEqual(response3.status_code, status.HTTP_201_CREATED)
            data3 = response3.data
            self.assertEqual(data3["type"], "analitico/stripe-subscription")
            self.assertEqual(data3["id"], data1["id"])
            self.assertEqual(data3["attributes"]["status"], "trialing")
            self.assertEqual(data3["attributes"]["plan"]["id"], TEST_BILLING_PLAN2_ID)

            # GET /api/billing/ws_xxx/subscription
            url = reverse("api:billing-subscription", args=(workspace.id,))
            response4 = self.client.get(url)
            self.assertEqual(response4.status_code, status.HTTP_200_OK)
            data4 = response4.data
            self.assertEqual(data4["id"], data1["id"])
            self.assertEqual(data4["attributes"]["plan"]["id"], TEST_BILLING_PLAN2_ID)
            self.assertEqual(data4["attributes"]["cancel_at_period_end"], False)

            # GET /api/billing/ws_xxx/invoice
            url = reverse("api:billing-invoices", args=(workspace.id,))
            response5 = self.client.get(url)
            self.assertEqual(response5.status_code, status.HTTP_200_OK)

            # POST /api/billing/ws_xxx/subscription (cancel plan)
            url = reverse("api:billing-subscription", args=(workspace.id,))
            response6 = self.client.delete(url)
            self.assertEqual(response6.status_code, status.HTTP_200_OK)
            data6 = response6.data
            self.assertEqual(data6["id"], data1["id"])
            self.assertEqual(data6["attributes"]["cancel_at_period_end"], True)

        except Exception as exc:
            logger.error(exc)
            raise exc

        finally:
            if subscription:
                # needs to be deleted because cancel method will cancel at period end, not now
                stripe.Subscription.delete(subscription.id)
            if workspace:
                workspace.delete()
