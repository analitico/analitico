import string
import random

from django.urls import reverse
from rest_framework import status

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

import api.models.log
from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import AnaliticoApiTestCase

# https://kapeli.com/cheat_sheets/Python_unittest_Assertions.docset/Contents/Resources/Documents/index

CHARACTERS = (
    "Winnie-the-Pooh",
    "Christopher Robin",
    "Piglet",
    "Eeyore",
    "Kanga",
    "Roo",
    "Tigger",
    "Rabbit",
    "Owl",
    "Bees",
    "Heffalumps",
    "Jagulars",
)


class FiltersTests(AnaliticoApiTestCase):
    """ 
    Test APIs filters like paging, sorting, ordering, searching, etc... 
    Most tests run on notebook but these filters are applied to all models.
    """

    logger = factory.logger

    def get_random_filtered_items(self, filter, n=100, asserts=True):
        """ Create some random items to be used for sorting, search, etc """
        for i in range(0, n):
            title = random.choice(CHARACTERS) + " " + "".join([random.choice(string.ascii_letters) for i in range(8)])
            nb = Notebook(workspace=self.ws1, title=title)
            nb.save()

        assert filter[0] == "?"
        url = reverse("api:notebook-list") + filter
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")
        if asserts:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), n)
        return response.data

    def setUp(self):
        self.setup_basics()
        try:
            url = reverse("api:workspace-list")
            self.upload_items(url, analitico.WORKSPACE_PREFIX)

            url = reverse("api:dataset-list")
            self.upload_items(url, analitico.DATASET_PREFIX)

        except Exception as exc:
            print(exc)
            raise exc

    def create_items(self, number_of_items):
        for i in range(0, number_of_items):
            item = Notebook(workspace=self.ws1, title=f"item {i}")
            item.save()

    def test_filters_paging_auto_off(self):
        """ Small sets are not paged by default """
        num_items = DEFAULT_PAGE_SIZE - 3
        self.create_items(num_items)

        url = reverse("api:notebook-list")
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
        self.create_items(num_items)

        url = reverse("api:notebook-list")
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
        self.create_items(num_items)

        url = reverse("api:notebook-list")
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
        self.create_items(num_items)

        url = reverse("api:notebook-list")
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

            for i, item in enumerate(data["data"]):
                # logs are sorted newest to oldest
                item_index = num_items - (((page - 1) * page_size) + i) - 1
                self.assertEqual(item["attributes"]["title"], "item {}".format(item_index))

    def test_filters_sorting_by_title(self):
        data = self.get_random_filtered_items("?sort=title")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i - 1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_by_title_inverse(self):
        data = self.get_random_filtered_items("?sort=-title")
        for i in range(1, len(data)):
            self.assertGreaterEqual(data[i - 1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_item_then_inverse_title(self):
        data = self.get_random_filtered_items("?sort=id,-title")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i - 1]["id"], data[i]["id"])

    def test_filters_sorting_level_item_title(self):
        data = self.get_random_filtered_items("?sort=id,title")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i - 1]["id"], data[i]["id"])
            if data[i - 1]["id"] == data[i]["id"]:
                self.assertLessEqual(data[i - 1]["attributes"]["title"], data[i]["attributes"]["title"])

    def test_filters_sorting_created_at(self):
        data = self.get_random_filtered_items("?sort=created_at")
        for i in range(1, len(data)):
            self.assertLessEqual(data[i - 1]["attributes"]["created_at"], data[i]["attributes"]["created_at"])

    def test_filters_sorting_created_at_inverse(self):
        data = self.get_random_filtered_items("?sort=-created_at")
        for i in range(1, len(data)):
            self.assertGreaterEqual(data[i - 1]["attributes"]["created_at"], data[i]["attributes"]["created_at"])

    def test_filters_sorting_invalid_field(self):
        for i in range(5):
            self.logger.info("test invalid sort %d", 1)
        url = reverse("api:notebook-list") + "?sort=bad"
        self.auth_token(self.token1)
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.status_text, "Bad Request")
        self.assertEqual(response.data["error"]["status"], "400")
        self.assertEqual(response.data["error"]["code"], "invalid")

    def test_filters_title(self):
        character = random.choice(CHARACTERS)
        data = self.get_random_filtered_items("?filter[search]=" + character, asserts=False)

        # search models directly, compare numbers
        items = Notebook.objects.filter(title__contains=character).all()
        self.assertEqual(len(items), len(data))
        for item in data:
            self.assertIn(character, item["attributes"]["title"])

    def test_filters_search_case_insensitive(self):
        character = random.choice(CHARACTERS)
        url = "?filter[search]=" + character.upper()
        data = self.get_random_filtered_items(url, asserts=False)

        # search models directly, compare numbers
        items = Notebook.objects.filter(title__icontains=character).all()
        self.assertEqual(len(items), len(data))
        for item in data:
            self.assertIn(character, item["attributes"]["title"])

    def test_filters_search_noresults(self):
        url = "?filter[search]=MISSING"
        data = self.get_random_filtered_items(url, asserts=False)
        self.assertEqual(len(data), 0)

    def test_filters_filter_title_exact(self):
        # search wuithout finding
        character = random.choice(CHARACTERS)
        url = "?filter[title]=" + character
        data = self.get_random_filtered_items(url, asserts=False)
        self.assertEqual(len(data), 0)

        # search and find exact
        item = Notebook.objects.filter(title__icontains=character).first()
        url = reverse("api:notebook-list") + "?filter[title]=" + item.title
        response = self.client.get(url, format="json")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["attributes"]["title"], item.title)

        # ?filter[title.contains] just character
        item = Notebook.objects.filter(title__icontains=character).first()
        url = reverse("api:notebook-list") + "?filter[title.contains]=" + character
        response = self.client.get(url, format="json")
        self.assertGreaterEqual(len(response.data), 1)
        self.assertIn(character, response.data[0]["attributes"]["title"])

        # ?filter[title.contains] full title
        item = Notebook.objects.filter(title__icontains=character).first()
        url = reverse("api:notebook-list") + "?filter[title.contains]=" + item.title
        response = self.client.get(url, format="json")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["attributes"]["title"], item.title)

        # ?filter[title.contains] wrong case
        item = Notebook.objects.filter(title__icontains=character).first()
        url = reverse("api:notebook-list") + "?filter[title.contains]=" + item.title.upper()
        response = self.client.get(url, format="json")
        self.assertEqual(len(response.data), 1)  # mysql finds it anyway

        # ?filter[title.contains] wrong case with case insensitive search
        item = Notebook.objects.filter(title__icontains=character).first()
        url = reverse("api:notebook-list") + "?filter[title.icontains]=" + item.title.upper()
        response = self.client.get(url, format="json")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["attributes"]["title"], item.title)

    ##
    ## Filters
    ##

    def test_filters_fields(self):
        """ Test ?field= to select only certain fields in the response """
        item = self.get_item(analitico.DATASET_TYPE, "ds_titanic_3", self.token1)
        self.assertEqual(item["id"], "ds_titanic_3")
        self.assertEqual(len(item["attributes"]), 8)

        fields = ("title", "description", "workspace_id")
        item = self.get_item(analitico.DATASET_TYPE, "ds_titanic_3", self.token1, query="?fields=" + ",".join(fields))
        self.assertEqual(len(item["attributes"]), 3)

        # all requested fields have been returned?
        for field in fields:
            self.assertIn(field, item["attributes"])

        # all returned fields have been requested?
        for attribute in item["attributes"]:
            self.assertIn(attribute, fields)

        self.assertEqual(item["attributes"]["title"], "Kaggle - Titanic training dataset (train.csv)")
        self.assertEqual(item["attributes"]["description"], "https://www.kaggle.com/c/titanic")
        self.assertEqual(item["attributes"]["workspace_id"], "ws_samples")

    def test_filters_fields_missing_field(self):
        """ Test ?field= to select fields which do not exist (should be ignored) """
        fields = ("title", "description", "workspace_id", "FAKEFIELD")
        item = self.get_item(analitico.DATASET_TYPE, "ds_titanic_3", self.token1, query="?fields=" + ",".join(fields))
        self.assertEqual(len(item["attributes"]), 3)

        # all returned fields have been requested?
        for attribute in item["attributes"]:
            self.assertIn(attribute, fields)

        # no FAKEFIELD
        self.assertNotIn("FAKEFIELD", item["attributes"])
