import pytest
import urllib

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
        state1 = api.slack.slack_get_state("ws_user1")
        state2 = api.slack.slack_get_state("ws_user1")
        self.assertNotEqual(state1, "ws_user1")
        self.assertTrue(state1.startswith("ws_user1"))
        self.assertEqual(state1, state2)

    def test_slack_get_state_different(self):
        """ State string used for oauth validation differs by workspace """
        state1 = api.slack.slack_get_state("ws_user1")
        state2 = api.slack.slack_get_state("ws_user2")
        self.assertNotEqual(state1, state2)

    def test_slack_get_button_url(self):
        """ Slack button url and html are customized for specific workspace integration """
        url = reverse("api:workspace-detail", args=("ws_user1",))
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
        self.assertIn("ws_user1", slack_button_html)
        self.assertIn("ws_user1", slack_button_url)

    def test_slack_oauth_no_state(self):
        """ Calling our slack oauth endpoint without a valid, signed state """
        url = reverse("api:workspace-slack-oauth", args=("ws_user1",))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_slack_oauth_with_state_no_code(self):
        """ Calling our slack oauth endpoint with a valid slack code """
        state = urllib.parse.quote(api.slack.slack_get_state("ws_user1"))
        url = reverse("api:workspace-slack-oauth", args=("ws_user1",)) + "?state=" + state
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["title"], "Slack returned error: invalid_code")
