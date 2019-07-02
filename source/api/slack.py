import requests
import urllib
import os
import datetime

from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.core.signing import Signer
from rest_framework.request import Request

import analitico
import api

from analitico import logger, AnaliticoException
from analitico.utilities import get_dict_dot

from api.models import Job
from api.factory import factory
from api.utilities import get_query_parameter

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
SLACK_BUTTON_HTML = '<a href="$URL$"><img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x"></a>'

# url to exchange code with token
SLACK_OAUTH_ACCESS_URL = "https://slack.com/api/oauth.access"

# Submission guidelines for the Slack App Directory
# https://api.slack.com/docs/slack-apps-guidelines

# Slack oauth flow:
# https://api.slack.com/docs/oauth


def slack_get_state(item_id: str) -> str:
    """ Returns a secret that can be used to make sure the oauth was originated by analitico. """
    signer = Signer()
    value = signer.sign(item_id)
    return value


def slack_get_install_button_url(request: Request, item_id: str) -> str:
    """ Returns the url that can be used to display a button that can install the Slack app. """
    # oauth flow should redirect back to the same server that generates the link
    # django/gunicorn run behind nginx as a reverse proxy so we need to upgrade http to https
    redirect_uri = reverse("api:" + factory.get_item_type(item_id) + "-slack-oauth", args=(item_id,))
    redirect_uri = request.build_absolute_uri(redirect_uri)
    redirect_uri = redirect_uri.replace("http://", "https://")

    url = SLACK_BUTTON_URL.replace("$STATE$", urllib.parse.quote(slack_get_state(item_id)))
    url = url.replace("$REDIRECT$", urllib.parse.quote(redirect_uri))

    html = SLACK_BUTTON_HTML.replace("$URL$", url)
    return url, html


def slack_oauth_exchange_code_for_token(request: Request, item_id: str) -> bool:
    """ Handle callback from Slack to complete integrations of incoming webhooks. """
    try:
        # Using OAuth 2.0
        # https://api.slack.com/docs/oauth

        # oauth temporary code and state that we passed
        code = get_query_parameter(request, "code", None)
        state = get_query_parameter(request, "state", None)

        # remove query string
        redirect_uri = request.build_absolute_uri()
        redirect_uri = redirect_uri[: redirect_uri.index("?")]
        redirect_uri = redirect_uri.replace("http://", "https://")

        # validate state to make sure user is authorized to connect workspace
        if state != slack_get_state(item_id):
            raise PermissionDenied("?state= parameter was not signed properly.")

        # https://api.slack.com/methods/oauth.access
        params = {
            "client_id": SLACK_CLIENT_ID,
            "client_secret": SLACK_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        response = requests.post(SLACK_OAUTH_ACCESS_URL, params=params)
        if response.status_code != 200:
            raise AnaliticoException(
                f"slack_oauth_exchange_code_for_token - call to {SLACK_OAUTH_ACCESS_URL} returned status_code: {response.status_code}"
            )
        response_json = response.json()

        # store access credentials in workspace
        item = factory.get_item(item_id)
        item.set_attribute("slack", {"oauth": response_json})
        item.save()

        return True

    except Exception as exc:
        raise AnaliticoException(f"slack_oauth_exchange_code_for_token - {redirect_uri} raised {exc}") from exc


def slack_notify_job(job: Job) -> bool:
    """ Sends a notification to Slack (if configured) regarding the completion of this job """

    # links to job and target item
    item_id = job.item_id
    item = factory.get_item(item_id)
    item_url = f"https://analitico.ai/app/{item.type}s/{item_id}"
    job_url = f"{item_url}/jobs#{job.id}"

    # elapsed time
    elapsed_sec = int((job.updated_at - job.created_at).total_seconds())

    # message shows item name (if named)
    message = f"{item.title} _({item.id})_" if item.title else item_id
    message += "\n" + job_url

    # https://api.slack.com/incoming-webhooks
    # https://api.slack.com/docs/message-attachments
    message = {
        "text": f"Job {job.status} in {int(elapsed_sec/60):02d}:{elapsed_sec%60:02d}",
        "attachments": [
            {"text": message, "color": "good" if job.status == analitico.status.STATUS_COMPLETED else "danger"}
        ],
    }

    slack_conf_item = item
    slack_conf = item.get_attribute("slack")
    if not slack_conf and item.workspace:
        slack_conf_item = item.workspace
        slack_conf = item.workspace.get_attribute("slack")

    if slack_conf:
        weebhook_url = get_dict_dot(slack_conf, "oauth.incoming_webhook.url")
        if weebhook_url:
            response = requests.post(weebhook_url, json=message)
            if response.status_code != 200:
                logger.warning(f"slack_notify_job - {weebhook_url} returned status_code: {response.status_code}")
                if response.status_code == 404:
                    # user has removed this application from his workspace
                    logger.warning(f"slack_notify_job - removing slack configuration from {slack_conf_item.id}")
                    slack_conf_item.set_attribute("slack.oauth", None)
                    slack_conf_item.save()
        else:
            logger.warning(f"slack_notify_job - {item_id} has 'slack' config but no webhook_url")

    # testing webhook for analitico's own workspace
    if SLACK_INTERNAL_WEBHOOK:
        message["text"] += " (internal notification)"
        response = requests.post(SLACK_INTERNAL_WEBHOOK, json=message)
        if response.status_code != 200:
            logger.warning(f"slack_notify_job - analitico webhook returned status_code: {response.status_code}")

    return True
