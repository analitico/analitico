import os
import requests
import logging

SLACK_INTERNAL_WEBHOOK = os.environ["ANALITICO_SLACK_INTERNAL_WEBHOOK"]


def slack_send_internal_notification(text: str, attachment: str, color=None) -> bool:
    """ 
    Sends a notification to Slack to the internal analitico channel. 
    
    Parameters:
    text (str): The main text of the notification
    attachment (str): Longer attached text (optional)
    color (str): Color of attachment, eg: good, warning, danger, #231212
    """
    message = {"text": text + "\n_Internal Notification_"}

    if attachment:
        message["attachments"] = [{"text": attachment, "color": color if color else "good"}]

    response = requests.post(SLACK_INTERNAL_WEBHOOK, json=message)
    if response.status_code != 200:
        msg = f"slack_notify_job - analitico webhook returned status_code: {response.status_code}"
        logging.warning(msg)

    return True
