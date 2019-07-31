import pytest
import urllib
import datetime
import logging
import time

from django.urls import reverse
from rest_framework import status

import api
import api.notifications
from api.models import Recipe, Dataset
from analitico.utilities import get_dict_dot
from .utils import AnaliticoApiTestCase

import django.core.mail


@pytest.mark.django_db
class SlackTests(AnaliticoApiTestCase):
    def setUp(self):
        self.setup_basics()

    ##
    ## Slack methods
    ##

    def test_get_signed_secret_consistent(self):
        """ State string used for oauth validation is consistent over time """
        state1 = api.utilities.get_signed_secret("ws_001")
        state2 = api.utilities.get_signed_secret("ws_001")
        self.assertNotEqual(state1, "ws_001")
        self.assertTrue(state1.startswith("ws_001"))
        self.assertEqual(state1, state2)

    def test_get_signed_secret_different(self):
        """ State string used for oauth validation differs by workspace """
        state1 = api.utilities.get_signed_secret("ws_001")
        state2 = api.utilities.get_signed_secret("ws_002")
        self.assertNotEqual(state1, state2)

    def test_slack_get_button_url(self):
        """ Slack button url and html are customized for specific workspace integration """
        url = reverse("api:workspace-detail", args=("ws_001",))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.auth_token(self.token1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        slack = response.data["attributes"]["slack"]
        slack_button_url = slack["button"]["url"]
        slack_button_html = slack["button"]["html"]

        self.assertIn('<a href="https://slack.com/oauth/authorize?client_id=', slack_button_html)
        self.assertIn("https://slack.com/oauth/authorize?client_id=", slack_button_url)
        self.assertIn("ws_001", slack_button_html)
        self.assertIn("ws_001", slack_button_url)

    def test_slack_oauth_no_state(self):
        """ Calling our slack oauth endpoint without a valid, signed state """
        url = reverse("api:workspace-slack-oauth", args=("ws_001",))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_slack_oauth_with_state_no_code(self):
        """ Calling our slack oauth endpoint with a valid slack code """
        state = urllib.parse.quote(api.utilities.get_signed_secret("ws_001"))
        url = reverse("api:workspace-slack-oauth", args=("ws_001",)) + "?state=" + state
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["title"], "Slack returned error: invalid_code")

    def test_slack_send_internal_notification(self):
        api.notifications.slack_send_internal_notification(
            "This is a test on " + datetime.datetime.now().isoformat(),
            "About a month after we started Y Combinator we came up with the phrase that became our motto: Make something people want. We've learned a lot since then, but if I were choosing now that's still the one I'd pick. "
            "Another thing we tell founders is not to worry too much about the business model, at least at first. Not because making money is unimportant, but because it's so much easier than building something great. "
            "A couple weeks ago I realized that if you put those two ideas together, you get something surprising. Make something people want. Don't worry too much about making money. What you've got is a description of a charity. "
            "When you get an unexpected result like this, it could either be a bug or a new discovery. Either businesses aren't supposed to be like charities, and we've proven by reductio ad absurdum that one or both of the principles we began with is false. Or we have a new idea. "
            "I suspect it's the latter, because as soon as this thought occurred to me, a whole bunch of other things fell into place.\n"
            "http://www.paulgraham.com/good.html",
        )

    ##
    ## Notifications
    ##

    def configure_test_notifications(self, item):
        item.set_attribute(
            "notifications",
            {
                "email": {
                    "prova1@analitico.ai": {"level": logging.INFO},
                    "prova2@analitico.ai": {"level": logging.ERROR},  # no email for success
                    "prova3@analitico.ai": {"level": logging.INFO},
                },
                "slack": {"level": logging.INFO},
            },
        )

    def test_notifications_get_job_completion_webhook(self):
        url1 = api.notifications.get_job_completion_webhook("ds_001", "jb_001")
        url2 = api.notifications.get_job_completion_webhook("ds_001", "jb_001")
        self.assertEqual(url1, url2)

        url1 = api.notifications.get_job_completion_webhook("ds_001", "jb_001")
        url2 = api.notifications.get_job_completion_webhook("ds_002", "jb_001")
        self.assertNotEqual(url1, url2)

    def test_notifications_job_completion_success(self):
        item = Recipe(id="rx_jmFuqwhjZGgS", workspace=self.ws1)
        self.configure_test_notifications(item)
        item.save()

        webhook_url = api.notifications.get_job_completion_webhook(item.id, "jb-jyffvhih")
        response = self.client.get(webhook_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # slack check
        self.assertEqual(response.data["attributes"]["slack"]["count"], 1)

        # emails
        self.assertEqual(response.data["attributes"]["email"]["count"], 2)
        outbox = django.core.mail.outbox
        self.assertEqual(len(outbox), 2)
        self.assertEqual(outbox[0].to[0], "prova1@analitico.ai")
        self.assertEqual(outbox[1].to[0], "prova3@analitico.ai")

    def test_notifications_job_completion_failure(self):
        item = Dataset(id="ds_hdxqnp7t", workspace=self.ws1)
        self.configure_test_notifications(item)
        item.save()

        webhook_url = api.notifications.get_job_completion_webhook(item.id, "jb-vz07l6ib")
        response = self.client.get(webhook_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # slack check
        self.assertEqual(response.data["attributes"]["slack"]["count"], 1)

        # emails
        self.assertEqual(response.data["attributes"]["email"]["count"], 3)
        outbox = django.core.mail.outbox
        self.assertEqual(len(outbox), 3)
        self.assertEqual(outbox[0].to[0], "prova1@analitico.ai")
        self.assertEqual(outbox[1].to[0], "prova2@analitico.ai")
        self.assertEqual(outbox[2].to[0], "prova3@analitico.ai")

    def test_notification_delay(self):
        item = Dataset(id="ds_hdxqnp7t", workspace=self.ws1)
        self.configure_test_notifications(item)
        item.save()

        start_time = time.time()
        delay = 5
        
        webhook_url = api.notifications.get_job_completion_webhook(item.id, "jb-jyffvhih", delay=delay)
        response = self.client.get(webhook_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # expecting immediate response from the request
        self.assertLess(time.time() - start_time, delay)