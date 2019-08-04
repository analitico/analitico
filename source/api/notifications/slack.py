import requests
import urllib
import os
import logging
import dateutil.parser

from django.urls import reverse
from rest_framework.request import Request
from rest_framework import status

import analitico
from analitico import logger, AnaliticoException
from analitico.utilities import get_dict_dot
from analitico.status import STATUS_COMPLETED, STATUS_FAILED

from api.factory import factory
from api.utilities import get_query_parameter, get_signed_secret

# https://api.slack.com/apps
SLACK_CLIENT_ID = os.environ["ANALITICO_SLACK_CLIENT_ID"]
SLACK_SECRET = os.environ["ANALITICO_SLACK_SECRET"]
SLACK_INTERNAL_WEBHOOK = os.environ["ANALITICO_SLACK_INTERNAL_WEBHOOK"]

assert SLACK_CLIENT_ID
assert SLACK_SECRET
assert SLACK_INTERNAL_WEBHOOK

# url to start an integration request
SLACK_BUTTON_URL = (
    "https://slack.com/oauth/authorize?client_id="
    + SLACK_CLIENT_ID
    + "&scope=incoming-webhook&state=$STATE$&redirect_uri=$REDIRECT$"
)

# html used to display a button that starts a request
SLACK_BUTTON_HTML = (
    '<a href="$URL$"><img alt="Add to Slack" height="40" width="139" '
    'src="https://platform.slack-edge.com/img/add_to_slack.png" '
    'srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, '
    'https://platform.slack-edge.com/img/add_to_slack@2x.png 2x"></a>'
)

# url to exchange code with token
SLACK_OAUTH_ACCESS_URL = "https://slack.com/api/oauth.access"

# Submission guidelines for the Slack App Directory
# https://api.slack.com/docs/slack-apps-guidelines

# Slack oauth flow:
# https://api.slack.com/docs/oauth


def slack_get_install_button_url(request: Request, item_id: str) -> str:
    """ Returns the url that can be used to display a button that can install the Slack app. """
    # oauth flow should redirect back to the same server that generates the link
    # django/gunicorn run behind nginx as a reverse proxy so we need to upgrade http to https
    redirect_uri = reverse("api:" + factory.get_item_type(item_id) + "-slack-oauth", args=(item_id,))
    redirect_uri = request.build_absolute_uri(redirect_uri)
    redirect_uri = redirect_uri.replace("http://", "https://")

    url = SLACK_BUTTON_URL.replace("$STATE$", urllib.parse.quote(get_signed_secret(item_id)))
    url = url.replace("$REDIRECT$", urllib.parse.quote(redirect_uri))

    html = SLACK_BUTTON_HTML.replace("$URL$", url)
    return url, html


def slack_oauth_exchange_code_for_token(request: Request, item_id: str) -> bool:
    """ Handle callback from Slack to complete integrations of incoming webhooks. """
    # Using OAuth 2.0
    # https://api.slack.com/docs/oauth

    # oauth temporary code and state that we passed
    code = get_query_parameter(request, "code", None)
    state = get_query_parameter(request, "state", None)

    # remove query string
    redirect_uri = request.build_absolute_uri()
    if redirect_uri.find("?") != -1:
        redirect_uri = redirect_uri[: redirect_uri.index("?")]
    redirect_uri = redirect_uri.replace("http://", "https://")

    # validate state to make sure user is authorized to connect workspace
    if state != get_signed_secret(item_id):
        raise AnaliticoException("?state= parameter was not signed properly.", status_code=status.HTTP_403_FORBIDDEN)

    # https://api.slack.com/methods/oauth.access
    params = {"client_id": SLACK_CLIENT_ID, "client_secret": SLACK_SECRET, "code": code, "redirect_uri": redirect_uri}

    # send slack the codes, retrieve valid access token and endpoint url
    response = requests.post(SLACK_OAUTH_ACCESS_URL, params=params)
    if response.status_code != status.HTTP_200_OK:
        message = f"slack_oauth_exchange_code_for_token - call to {SLACK_OAUTH_ACCESS_URL} returned status_code: {response.status_code}"
        raise AnaliticoException(message, status_code=response.status_code)
    response_json = response.json()
    if not response_json["ok"]:
        raise AnaliticoException(f"Slack returned error: {response_json['error']}", status_code=400)

    # store access credentials in workspace
    item = factory.get_item(item_id)
    item.set_attribute("slack", {"oauth": response_json})
    item.save()

    return True


def slack_notify(item, message, level) -> {}:
    """ Sends a notification to Slack (if configured for this item) """
    count = 0

    slack_conf_item = item
    slack_conf = item.get_attribute("slack")
    if not slack_conf and item.workspace:
        slack_conf_item = item.workspace
        slack_conf = item.workspace.get_attribute("slack")

    if slack_conf:
        weebhook_url = get_dict_dot(slack_conf, "oauth.incoming_webhook.url")
        if weebhook_url:
            slack_level = int(slack_conf.get("level", logging.INFO))
            if level >= slack_level:
                response = requests.post(weebhook_url, json=message)
                if response.status_code == 200:
                    count += 1
                else:
                    msg = f"slack_notify_job - {weebhook_url} returned status_code: {response.status_code}"
                    logger.warning(msg)
                    if response.status_code == 404:
                        # user has removed this application from his workspace
                        msg = f"slack_notify_job - removing slack configuration from {slack_conf_item.id}"
                        logger.warning(msg)
                        slack_conf_item.set_attribute("slack.oauth", None)
                        slack_conf_item.save()
        else:
            logger.warning("slack_notify_job - %s has 'slack' config but no webhook_url", item.id)

    # testing webhook for analitico's own workspace
    if SLACK_INTERNAL_WEBHOOK:
        message["text"] += "\n_Internal Notification_"
        response = requests.post(SLACK_INTERNAL_WEBHOOK, json=message)
        if response.status_code == 200:
            count += 1
        else:
            msg = f"slack_notify_job - analitico webhook returned status_code: {response.status_code}"
            logger.warning(msg)

    return {"count": count}


def slack_send_internal_notification(
    text: str = None, attachment: str = None, color=None, message=None, channel=None
) -> bool:
    """ 
    Sends a notification to Slack to the internal analitico channel. 
    
    Parameters:
    text (str): The main text of the notification
    attachment (str): Longer attached text (optional)
    color (str): Color of attachment, eg: good, warning, danger, #231212
    """

    webhook = SLACK_INTERNAL_WEBHOOK
    if channel == "stripe":
        webhook = "https://hooks.slack.com/services/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"

    if not webhook:
        return False

    if not message:
        message = {"text": text + "\n_Internal Notification_"}

        if attachment:
            message["attachments"] = [{"text": attachment, "color": color if color else "good"}]

    response = requests.post(webhook, json=message)
    if response.status_code != 200:
        msg = f"slack_notify_job - analitico webhook returned status_code: {response.status_code}"
        logging.warning(msg)

    return True
