
import logging
from api.models import ItemMixin
from django.core.mail import send_mail


def email_notify(item, message, level) -> dict:
    """
    Given an item and a notification message related to the item, this method will 
    check if email notifications are enabled and send them out. Notifications can be
    enabled at the item level or in the workspace. Each recipient is configured to
    receive notifications for a specific level (same as logging levels) and will only
    be sent the message if it's level is high enough.
    
    Arguments:
        item {[type]} -- An item that generated the notification message.
        message {[type]} -- A notification message in slack style dictionay.
        level {[type]} -- The notification level, eg: INFO is 20, WARNING 30, ERROR 40
    
    Returns:
        dict -- A count of emails sent and list of notified recipients.
    """
    result = {"count": 0, "recipients": []}

    # recipients can be configured in the specific item or at the workspace level
    item_conf = item.get_attribute("notifications.email", {}).copy()
    ws_conf = item.workspace.get_attribute("notifications.email", {}).copy()

    # if a recipient is configured in the item AND the workspace, the item prevails
    for key, value in item_conf.items():
        ws_conf[key] = value

    for to, to_conf in ws_conf.items():
        if level >= int(to_conf.get("level", logging.INFO)):
            # https://docs.djangoproject.com/en/2.2/topics/email/
            subject = message["text"].replace("\n", " ") # remove newlines
            send_mail(
                subject=subject,
                message=message["attachments"][0]["text"],
                from_email="notifications@analitico.ai",
                recipient_list=[to],
                fail_silently=False,
            )
            result["count"] = result["count"] + 1
            result["recipients"].append(to)

    return result
