import string
import random

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

# https://kapeli.com/cheat_sheets/Python_unittest_Assertions.docset/Contents/Resources/Documents/index

class FiltersTests(APITestCase):
    """ 
    Test APIs filters like paging, sorting, ordering, searching, etc... 
    Most tests run on logs because they are easy to create but these filters
    are applied to all models.
    """

    logger = factory.logger

    def get_random_filtered_logs(self, filter, n=100):
        """ Create some random log entries to be used for sorting various sorting, search, etc """
        for i in range(0, n):
            level = logging.INFO + random.randint(0,5)
            title = "title " + "".join([random.choice(string.ascii_letters) for i in range(8)])
            item_id = "pl_" + random.choice(string.digits) # fake plugin id (fewer choices so we have multiple logs per item_id)
            self.logger.log(level, title, item_id=item_id)

        assert filter[0] == "?"
        url = reverse("api:log-list") + filter
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), n)
        return response.data

    def setUp(self):
        self.setup_basics()

    def test_filters_paging_auto_off(self):
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

    def test_filters_paging_auto_off_largest(self):
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

    def test_filters_paging_auto_on_smallest(self):
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

    def test_filters_paging_large_set_uneven(self):
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


    def test_filters_sorting_by_title(self):
        data = self.get_random_filtered_logs("?sort=title")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i-1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_by_title_inverse(self):
        data = self.get_random_filtered_logs("?sort=-title")
        for i in range(1, len(data)):
            self.assertGreaterEqual(data[i-1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_item_then_title(self):
        data = self.get_random_filtered_logs("?sort=item_id,title")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i-1]["attributes"]["item_id"], data[i]["attributes"]["item_id"])
            if data[i-1]["attributes"]["item_id"] == data[i]["attributes"]["item_id"]:
                self.assertLessEqual(data[i-1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_title_then_item(self):
        data = self.get_random_filtered_logs("?sort=title,item_id")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i-1]["attributes"]["title"], data[i]["attributes"]["title"])
            if data[i-1]["attributes"]["title"] == data[i]["attributes"]["title"]:
                self.assertLessEqual(data[i-1]["attributes"]["item_id"], data[i]["attributes"]["item_id"])

    def test_filters_sorting_item_then_inverse_title(self):
        data = self.get_random_filtered_logs("?sort=item_id,-title")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i-1]["attributes"]["item_id"], data[i]["attributes"]["item_id"])
            if data[i-1]["attributes"]["item_id"] == data[i]["attributes"]["item_id"]:
                self.assertGreaterEqual(data[i-1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_item_inverse_then_inverse_title(self):
        data = self.get_random_filtered_logs("?sort=-item_id,-title")
        for i in range(1, len(data)):
            self.assertGreaterEqual(data[i-1]["attributes"]["item_id"], data[i]["attributes"]["item_id"])
            if data[i-1]["attributes"]["item_id"] == data[i]["attributes"]["item_id"]:
                self.assertGreaterEqual(data[i-1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_level_item_title(self):
        data = self.get_random_filtered_logs("?sort=level,item_id,title")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i-1]["attributes"]["level"], data[i]["attributes"]["level"])
            if data[i-1]["attributes"]["level"] == data[i]["attributes"]["level"]:
                self.assertLessEqual(data[i-1]["attributes"]["item_id"], data[i]["attributes"]["item_id"])
                if data[i-1]["attributes"]["item_id"] == data[i]["attributes"]["item_id"]:
                    self.assertLessEqual(data[i-1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_created_at(self):
        data = self.get_random_filtered_logs("?sort=created_at")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i-1]["attributes"]["created_at"], data[i]["attributes"]["created_at"])

    def test_filters_sorting_created_at_inverse(self):
        data = self.get_random_filtered_logs("?sort=-created_at")
        for i in range(1, len(data)):
            self.assertGreaterEqual(data[i-1]["attributes"]["created_at"], data[i]["attributes"]["created_at"])
