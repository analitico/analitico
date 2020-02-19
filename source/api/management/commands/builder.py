import os
import requests
import logging

from django.core.management.base import BaseCommand

from api.factory import factory
from api.k8 import k8_build_v2, k8_autodeploy


class Command(BaseCommand):
    def add_arguments(self, parser):
        # https://docs.djangoproject.com/en/2.1/howto/custom-management-commands/
        # https://docs.python.org/3/library/argparse.html#module-argparse
        self.help = "Take a recipe_id followed by a model_it and build a docker of the recipe into the model."
        parser.add_argument("item_id", nargs="*", type=str, help=self.help)

    def try_request_notification(self, notification_url):
        try:
            requests.get(notification_url)
            logging.info("Notification requested")
        except Exception:
            logging.warning("Failed to request the notification", exec_info=True)

    def handle(self, *args, **options):
        item_id = options["item_id"][0]
        target_id = options["item_id"][1]
        notebook = options["item_id"][2]

        item = factory.get_item(item_id)  # the recipe
        target = factory.get_item(target_id)  # the model
        job_data = {"notebook": notebook}  # the notebook name
        try:
            k8_build_v2(item, target, job_data)
            
            autodeploy = item.get_attribute("autodeploy")
            if autodeploy:
                k8_autodeploy(target, item, config=autodeploy)
        finally:
            notification_url = os.environ.get("ANALITICO_NOTIFICATION_URL")
            if notification_url:
                self.try_request_notification(notification_url)

        return 0
