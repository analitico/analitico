import os
import os.path
import numpy as np
import pandas as pd
import tempfile
import random
import string
import pytest
import sklearn
import sklearn.datasets
import urllib.parse

from django.test import tag
from django.urls import reverse

from rest_framework import status
from analitico.utilities import time_ms

import analitico
import analitico.plugin
import api.models

from analitico import logger
from analitico.pandas import pd_read_csv
from .utils import AnaliticoApiTestCase, ASSETS_PATH
from api.pagination import MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member
# pylint: disable=unused-variable


@pytest.mark.django_db
class BillingTests(AnaliticoApiTestCase):
    """ Test billing APIs and webhooks. """

    def setUp(self):
        self.setup_basics()

    def test_billing_strip_webhook_no_data(self):
        # url = reverse("api:billing-stripe-webhook")
        url = reverse("api:workspace-billing-stripe-webhook")
        response = self.client.post(url, {"type": "analitico.unittest"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
