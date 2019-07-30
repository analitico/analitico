import requests
import urllib
import os
import logging
import dateutil.parser
import urllib.parse

from django.urls import reverse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

import analitico
from analitico import logger, AnaliticoException
from analitico.utilities import get_dict_dot
from analitico.status import STATUS_COMPLETED, STATUS_FAILED

from api.factory import factory
from api.utilities import get_query_parameter, get_signed_secret

from analitico import AnaliticoException
from api.factory import factory
from api.k8 import k8_jobs_get
import api.utilities
import api.views

from .slack import slack_notify
from .email import email_notify


def _get_job_secret(item_id: str, job_id: str):
    return api.utilities.get_signed_secret(f"{item_id}-{job_id}")


def _notify_job(item_id: str, job_id: str):
    item = factory.get_item(item_id)
    job = k8_jobs_get(item, job_id)

    # links to job and target item
    item_url = f"https://analitico.ai/app/{item.type}s/{item.id}"

    job_id = job["metadata"]["name"]
    job_url = f"{item_url}/jobs#{job_id}"
    job_succeeded = int(get_dict_dot(job, "status.succeeded", 0))
    job_status = STATUS_COMPLETED if job_succeeded else STATUS_FAILED

    # notification level
    level = logging.INFO if job_succeeded else logging.ERROR

    # elapsed time (if available)
    elapsed_sec = ""
    try:
        start_time = dateutil.parser.parse(job["status"]["startTime"])
        completion_time = dateutil.parser.parse(job["status"]["conditions"][0]["lastTransitionTime"])
        elapsed_sec = int((completion_time - start_time).total_seconds())
        elapsed_sec = f" in {int(elapsed_sec/60):02d}:{elapsed_sec%60:02d}"
    except Exception as exc:
        logger.warning("Can't extract completion time from job %s: %s", job_id, exc)

    # message shows item name (if named)
    message = f"{item.title} _({item.id})_" if item.title else item.id
    message += "\n" + job_url

    # https://api.slack.com/incoming-webhooks
    # https://api.slack.com/docs/message-attachments
    message = {
        "text": f"Job {job_status}{elapsed_sec}",
        "attachments": [
            {"text": message, "color": "good" if job_status == analitico.status.STATUS_COMPLETED else "danger"}
        ],
    }

    return {
        "type": "analitico/notifications",
        "attributes": {"slack": slack_notify(item, message, level), "email": email_notify(item, message, level)},
    }


def get_job_completion_webhook(item_id: str, job_id: str):
    secret = _get_job_secret(item_id, job_id)
    return (
        reverse("api:notifications-webhook")
        + "?notification=job"
        + "&item_id="
        + urllib.parse.quote(item_id)
        + "&job_id="
        + urllib.parse.quote(job_id)
        + "&secret="
        + urllib.parse.quote(secret)
    )


@api_view()
def notifications_webhook(request: Request) -> Response:
    """
    This webhook is called whenever we need to trigger a notification, for example when a job
    has completed and we need to warn the owner over slack or email. The complete url for a job
    notification is created using get_job_completion_webhook. This API can be called without
    any authentication and is secured by a signed secret which is created by the server and later
    rechecked before executing the notifications.
    """
    notification_type = api.utilities.get_query_parameter(request, "notification")
    item_id = api.utilities.get_query_parameter(request, "item_id", None)
    job_id = api.utilities.get_query_parameter(request, "job_id", None)

    # verify that the secret used to sign is there and is valid
    api.utilities.get_unsigned_secret(api.utilities.get_query_parameter(request, "secret"))

    # notifying of job completion over slack and email
    if notification_type == "job":
        return Response(_notify_job(item_id, job_id), status=status.HTTP_200_OK)

    return Response(status=status.HTTP_400_BAD_REQUEST)
