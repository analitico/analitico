from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

import api.models.log
from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import APITestCase


class PagingTests(APITestCase):
    """ Test paging of large sets """

    logger = factory.logger

    def setUp(self):
        self.setup_basics()

    def logs(self, n=None):
        """ Returns Log models stored by handler """
        return self.handler.logs[n] if n else self.handler.logs

    def setUp(self):
        self.setup_basics()

    def test_log_paging_auto_off(self):
        """ Small sets are not paged by default """
        num_items = DEFAULT_PAGE_SIZE - 3

        for i in range(0, num_items):
            self.logger.info("log %d", i)

        url = reverse("api:log-list")
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertNotIn("links", data)
        self.assertNotIn("meta", data)
        self.assertEqual(len(data), num_items)

    def test_log_paging_auto_off_largest(self):
        """ Small sets are not paged by default (just one record less than max) """
        num_items = MAX_PAGE_SIZE
        for i in range(0, num_items):
            self.logger.info("log %d", i)

        url = reverse("api:log-list")
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertNotIn("links", data)
        self.assertNotIn("meta", data)
        self.assertEqual(len(data), num_items)

    def test_log_paging_auto_on_smallest(self):
        """ Large sets are paged by default """
        num_items = MAX_PAGE_SIZE + 1

        for i in range(0, num_items):
            self.logger.info("log %d", i)

        url = reverse("api:log-list")
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn("first", data["links"])
        self.assertIn("last", data["links"])
        self.assertIn("next", data["links"])
        self.assertIn("prev", data["links"])
        self.assertEqual(len(data["data"]), DEFAULT_PAGE_SIZE)
        self.assertEqual(data["meta"]["pagination"]["count"], num_items)
        self.assertEqual(data["meta"]["pagination"]["page"], 1)
        self.assertEqual(data["meta"]["pagination"]["pages"], int(num_items / DEFAULT_PAGE_SIZE) + 1)

    def test_paging_large_set_uneven(self):
        """ Write lots of logs then read them in pages """
        num_pages = 12
        page_size = DEFAULT_PAGE_SIZE
        num_items = (page_size * num_pages) - 3

        for i in range(0, num_items):
            self.logger.info("log %d", i)

        url = reverse("api:log-list")
        for page in range(1, num_pages):
            page_url = "{}?{}={}".format(url, PAGE_PARAM, page)

            self.auth_token(self.token1)
            response = self.client.get(page_url, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.data

            self.assertIn("first", data["links"])
            self.assertIn("last", data["links"])
            self.assertIn("next", data["links"])
            self.assertIn("prev", data["links"])

            self.assertEqual(len(data["data"]), page_size - 3 if page == num_pages else page_size)
            self.assertEqual(data["meta"]["pagination"]["count"], num_items)
            self.assertEqual(data["meta"]["pagination"]["page"], page)
            self.assertEqual(data["meta"]["pagination"]["pages"], num_pages)

            for i, log in enumerate(data["data"]):
                log_index = ((page - 1) * page_size) + i
                self.assertEqual(log["attributes"]["title"], "log {}".format(log_index))
