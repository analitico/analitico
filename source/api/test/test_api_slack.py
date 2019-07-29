import pytest
import urllib
import datetime

from django.urls import reverse
from rest_framework import status

import api
from analitico.utilities import get_dict_dot
from .utils import AnaliticoApiTestCase


@pytest.mark.django_db
class SlackTests(AnaliticoApiTestCase):
    def setUp(self):
        self.setup_basics()

    ##
    ## Slack methods
    ##

    def test_slack_get_state_consistent(self):
        """ State string used for oauth validation is consistent over time """
        state1 = api.slack.slack_get_state("ws_001")
        state2 = api.slack.slack_get_state("ws_001")
        self.assertNotEqual(state1, "ws_001")
        self.assertTrue(state1.startswith("ws_001"))
        self.assertEqual(state1, state2)

    def test_slack_get_state_different(self):
        """ State string used for oauth validation differs by workspace """
        state1 = api.slack.slack_get_state("ws_001")
        state2 = api.slack.slack_get_state("ws_002")
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
        state = urllib.parse.quote(api.slack.slack_get_state("ws_001"))
        url = reverse("api:workspace-slack-oauth", args=("ws_001",)) + "?state=" + state
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["title"], "Slack returned error: invalid_code")

    def test_slack_send_internal_notification(self):
        api.slack.slack_send_internal_notification(
            "This is a test on " + datetime.datetime.now().isoformat(),
            "About a month after we started Y Combinator we came up with the phrase that became our motto: Make something people want. We've learned a lot since then, but if I were choosing now that's still the one I'd pick. "
            "Another thing we tell founders is not to worry too much about the business model, at least at first. Not because making money is unimportant, but because it's so much easier than building something great. "
            "A couple weeks ago I realized that if you put those two ideas together, you get something surprising. Make something people want. Don't worry too much about making money. What you've got is a description of a charity. "
            "When you get an unexpected result like this, it could either be a bug or a new discovery. Either businesses aren't supposed to be like charities, and we've proven by reductio ad absurdum that one or both of the principles we began with is false. Or we have a new idea. "
            "I suspect it's the latter, because as soon as this thought occurred to me, a whole bunch of other things fell into place.\n"
            "http://www.paulgraham.com/good.html",
        )
