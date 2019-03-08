from analitico import TYPE_PREFIX, USER_TYPE
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .utils import APITestCase

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

from analitico.utilities import logger

import analitico.models


class LogTests(APITestCase):
    """ Test log operations like collecting logs and returning them as log entries via APIs """

    def setUp(self):
        self.setup_basics()

    def test_log_info(self):
        logger.info("info message %d", 1)
        logger.info("info message %d", 2)
        logger.info("info message %d", 3)

        url = reverse("api:log-list")
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        # TODO test

