import io
import os
import os.path
import numpy as np
import pandas as pd
import tempfile
import random
import string

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime
from django.core.files.uploadedfile import SimpleUploadedFile

import django.utils.http
import django.core.files

from rest_framework import status
from rest_framework.test import APITestCase
from analitico.utilities import read_json, get_dict_dot, time_ms, logger

import analitico.plugin
import api.models
from api.models import User, USER_PREFIX, USER_TYPE
from .utils import APITestCase
from analitico import ACTION_PROCESS
from api.pagination import MIN_PAGE_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE
from api.models import ASSETS_CLASS_DATA, ASSETS_CLASS_ASSETS

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class UserTests(APITestCase):
    """ Test user operations like retrieving and updating the logged in user's profile """

    def setUp(self):
        self.setup_basics()

    def test_user_get_profile(self):
        """ Test getting a logged in user profile """
        url = reverse("api:user-me")
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = response.data
        self.assertEqual(user["type"], USER_TYPE)
        self.assertTrue("attributes" in user)
        attributes = user["attributes"]
        self.assertTrue("password" not in attributes)
