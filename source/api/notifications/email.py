import logging
import yaml

from pathlib import Path
from analitico.utilities import read_text
from api.models import ItemMixin, User
from api.utilities import read_yaml
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives

def email_send_template(user: User, template_name: str, **kwargs):
    """
    Sends a customized email to a specific user from a given template.
    
    Arguments:
        user {User} -- User that we should send the email to
        template_name {str} -- Name of the email template, eg: password-reset.yaml
    """

    kwargs["user"] = user
    kwargs["email"] = user.email
    kwargs["first_name"] = user.first_name
    kwargs["last_name"] = user.last_name

    template_yaml = read_yaml(Path(__file__).parent / "templates" / template_name)
    subject = template_yaml["subject"].format(**kwargs)
    
    message_html = template_yaml["message"].format(**kwargs)
    message_text = strip_tags(message_html) # Strip the html tag. So people can see the pure text at least.

    # create the email, and attach the HTML version as well.
    msg = EmailMultiAlternatives(subject, message_text, template_yaml["from"], [user.email])
    msg.attach_alternative(message_html, "text/html")
    msg.send()


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
            subject = message["text"].replace("\n", " ")  # remove newlines
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
