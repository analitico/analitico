from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

import api.models.log
from api.models import Log, Recipe
from api.factory import factory
from api.models.log import *

from .utils import APITestCase


class LogTests(APITestCase):
    """ Test log operations like collecting logs and returning them as log entries via APIs """

    logger = factory.logger

    def logs(self, n=None):
        """ Returns Log models stored by handler """
        return self.handler.logs[n] if n else self.handler.logs

    def setUp(self):
        self.setup_basics()
        # self.handler.clear()

    def test_log_model(self):
        log = Log()
        log.id = "lg_001"
        log.save()

        logs = Log.objects.all()
        log_1 = logs[0]
        self.assertEqual(log_1.id, "lg_001")

    def test_log_basics(self):
        self.logger.info("info message")
        logs = Log.objects.all()

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].id[: len(analitico.LOG_PREFIX)], analitico.LOG_PREFIX)
        self.assertEqual(logs[0].message, "info message")

    def test_log_level(self):
        self.logger.debug("debug message")
        self.logger.info("info message")
        self.logger.warning("warning message")
        self.logger.error("error message")  # this triggers Sentry to send useless report :(
        logs = Log.objects.all()

        # debug message was NOT logged to database
        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[1].level, logging.WARNING)
        self.assertEqual(logs[2].level, logging.ERROR)

    def test_log_formatting(self):
        self.logger.info("info message %d", 1)
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].level_name, "INFO")
        self.assertEqual(logs[0].message, "info message 1")
        self.assertEqual(logs[0].name, "analitico")

    def test_log_formatting_2(self):
        self.logger.info("info message %d, %s", 1, "pippo")
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].message, "info message 1, pippo")

    def test_log_formatting_plus_attrs(self):
        self.logger.info("info message %d, %s", 1, "mickey", more1="more_value")
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].message, "info message 1, mickey")
        self.assertEqual(logs[0].attributes["more1"], "more_value")

    def test_log_formatting_plus_recipe_1(self):
        """ Recipe model parameter is converted to recipe_id when stored in Log """
        recipe = Recipe()
        self.logger.info("info message %d, %s", 1, "mickey", recipe=recipe)
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].message, "info message 1, mickey")
        self.assertEqual(logs[0].attributes["recipe_id"], recipe.id)

    def test_log_formatting_plus_recipe_2(self):
        """ Recipe model parameter is converted to recipe_id when stored in Log and also added as item_id """
        recipe = Recipe()
        self.logger.info("info message %d, %s", 1, "mickey", recipe=recipe, item=recipe)
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].message, "info message 1, mickey")
        self.assertEqual(logs[0].item_id, recipe.id)
        self.assertEqual(logs[0].attributes["recipe_id"], recipe.id)
