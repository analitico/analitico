import io
import os
import os.path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.http.response import StreamingHttpResponse
from django.utils.dateparse import parse_datetime

import django.utils.http
import django.core.files
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.staticfiles.templatetags.staticfiles import static
from analitico.utilities import read_json, get_dict_dot
from django.test import TestCase, override_settings

import api.models
import api.test

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class WebsiteTests(api.test.APITestCase):

    ##
    ## Login, etc
    ##

    def test_lab_redirects_if_not_authenticated(self):
        """ Test that user needs to be authenticated to access /lab and will be redirected if not. """
        response = self.client.get("/lab")
        self.assertRedirects(response, "/accounts/login/?next=/lab")
