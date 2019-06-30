
import requests

import analitico
import api

from api.models import Job
from api.factory import factory

# testing webhook for analitico's own workspace
SLACK_WEBHOOK = "https://hooks.slack.com/services/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"

# Submission guidelines for the Slack App Directory
# https://api.slack.com/docs/slack-apps-guidelines


def slack_notify_job(job: Job) -> bool:
    """ Sends a notification to Slack (if configured) regarding the completion of this job """

    # links to job and target item
    item_id = job.item_id
    item_type = factory.get_item_type(item_id)
    item_url = f"https://analitico.ai/app/{item_type}s/{item_id}"
    job_url = f"{item_url}/jobs#{job.id}"

    # https://api.slack.com/incoming-webhooks
    # https://api.slack.com/docs/message-attachments
    message = {
        "text": f"Job completed with status: *{job.status}*\n",
        "attachments": [
            {"text": f"{job_url}", "color": "good" if job.status == analitico.status.STATUS_COMPLETED else "danger"}
        ],
    }

    if SLACK_WEBHOOK:
        requests.post(SLACK_WEBHOOK, json=message)

    return True
