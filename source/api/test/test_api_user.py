import copy
from base64 import b64encode

from analitico import TYPE_PREFIX, USER_TYPE
from django.urls import reverse
from rest_framework import status
from .utils import AnaliticoApiTestCase

from api.models import User

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

TEST_USER_EMAIL = "paperino@disney.com"
TEST_USER_PASSWORD = "testingIsFun"
TEST_USER = {
    "type": "analitico/user",
    "id": TEST_USER_EMAIL,
    "attributes": {"first_name": "Paolino", "last_name": "Paperino", "shoe_size": 14},
}
TEST_USER_WITH_PASSWORD = copy.deepcopy(TEST_USER)
TEST_USER_WITH_PASSWORD["attributes"]["password"] = TEST_USER_PASSWORD


class UserTests(AnaliticoApiTestCase):
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
        self.assertEqual(user["type"], TYPE_PREFIX + USER_TYPE)
        self.assertEqual(user["id"], "user1@analitico.ai")
        self.assertTrue("attributes" in user)
        attributes = user["attributes"]
        self.assertTrue("password" not in attributes)
        self.assertEqual(attributes["is_staff"], True)
        self.assertEqual(attributes["is_superuser"], True)

    def test_user_get_profile_user2(self):
        url = reverse("api:user-me")
        self.auth_token(self.token2)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = response.data
        self.assertEqual(user["type"], TYPE_PREFIX + USER_TYPE)
        self.assertEqual(user["id"], "user2@analitico.ai")
        self.assertTrue("attributes" in user)
        attributes = user["attributes"]
        self.assertTrue("password" not in attributes)
        self.assertEqual(attributes["is_staff"], False)
        self.assertEqual(attributes["is_superuser"], False)

    def test_user_get_profile_by_email(self):
        self.auth_token(self.token1)
        # self, ok!
        url = reverse("api:user-detail", args=("user1@analitico.ai",))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # others, ok because admin
        url = reverse("api:user-detail", args=("user2@analitico.ai",))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_get_profile_by_email_no_auth(self):
        self.auth_token(self.token2)
        # self, ok!
        url = reverse("api:user-detail", args=("user2@analitico.ai",))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # others, deny because not admin
        url = reverse("api:user-detail", args=("user1@analitico.ai",))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_create(self):
        url = reverse("api:user-list")
        self.auth_token(self.token1)
        response = self.client.post(url, TEST_USER, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = response.data
        self.assertEqual(user["type"], TYPE_PREFIX + USER_TYPE)
        self.assertTrue("attributes" in user)
        attributes = user["attributes"]
        self.assertEqual(attributes["first_name"], "Paolino")
        self.assertEqual(attributes["last_name"], "Paperino")
        self.assertEqual(attributes["shoe_size"], 14)

    def test_user_create_no_email(self):
        url = reverse("api:user-list")
        self.auth_token(self.token1)
        user_without_id = {
            "type": "analitico/user",
            "attributes": {"first_name": "Paolino", "last_name": "Paperino", "shoe_size": 14},
        }
        response = self.client.post(url, user_without_id, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.data
        self.assertTrue("error" in data)
        error = data["error"]
        self.assertEqual(error["status"], "400")

    def test_user_create_then_retrieve(self):
        url = reverse("api:user-list")
        self.auth_token(self.token1)
        response = self.client.post(url, TEST_USER, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        url = reverse("api:user-detail", args=("paperino@disney.com",))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = response.data
        self.assertEqual(user["type"], TYPE_PREFIX + USER_TYPE)
        self.assertTrue("attributes" in user)
        attributes = user["attributes"]
        self.assertEqual(attributes["first_name"], "Paolino")
        self.assertEqual(attributes["last_name"], "Paperino")
        self.assertEqual(attributes["shoe_size"], 14)

    def test_user_modify_then_retrieve(self):
        self.auth_token(self.token2)
        url = reverse("api:user-detail", args=("user2@analitico.ai",))
        changes = {"id": "user2@analitico.ai", "first_name": "Mickey", "shoe_size": 8}
        response = self.client.put(url, changes, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check changes
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = response.data
        self.assertEqual(user["type"], TYPE_PREFIX + USER_TYPE)
        self.assertTrue("attributes" in user)
        attributes = user["attributes"]
        self.assertEqual(attributes["first_name"], "Mickey")
        self.assertEqual(attributes["last_name"], "")
        self.assertEqual(attributes["shoe_size"], 8)

        # remove name and shoe_size
        changes = {"id": "user2@analitico.ai", "first_name": "", "shoe_size": None}
        response = self.client.put(url, changes, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check changes
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = response.data
        self.assertEqual(user["type"], TYPE_PREFIX + USER_TYPE)
        self.assertTrue("attributes" in user)
        attributes = user["attributes"]
        self.assertEqual(attributes["first_name"], "")
        self.assertTrue("shoe_size" not in attributes)

    def test_user_modify_other_user_no_auth(self):
        """ Authenticate as user2@analitico.ai (a regular user) then try to modify user1@analitico.ai """
        self.auth_token(self.token2)
        url = reverse("api:user-detail", args=("user1@analitico.ai",))
        changes = {"id": "user1@analitico.ai", "first_name": "Mickey", "shoe_size": 8}
        response = self.client.put(url, changes, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_modify_other_user_as_superuser(self):
        """ Authenticate as user1@analitico.ai (a super user) then try to modify user2@analitico.ai """
        self.auth_token(self.token1)
        url = reverse("api:user-detail", args=("user2@analitico.ai",))
        changes = {"id": "user2@analitico.ai", "first_name": "Mickey", "shoe_size": 8}
        response = self.client.put(url, changes, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_delete(self):
        self.auth_token(self.token1)
        url = reverse("api:user-detail", args=("user1@analitico.ai",))
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # now try to retrieve deleted user, token should also have been deleted
        # so we should get a 401 (not a regular 404)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_delete_other_user_no_auth(self):
        self.auth_token(self.token2)
        url = reverse("api:user-detail", args=("user1@analitico.ai",))
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_delete_other_user_as_superuser(self):
        self.auth_token(self.token1)
        url = reverse("api:user-detail", args=("user2@analitico.ai",))
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # now retrieve deleted user
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    ##
    ## Sign in, Sign up, Sign out
    ##

    def test_user_signup(self):
        url = reverse("api:user-signup")
        response = self.client.post(url, TEST_USER_WITH_PASSWORD, format="json")  # NO AUTH TOKEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = response.data
        self.assertEqual(user["type"], TYPE_PREFIX + USER_TYPE)
        self.assertTrue("attributes" in user)
        attributes = user["attributes"]

        self.assertEqual(attributes["is_staff"], False)
        self.assertEqual(attributes["is_superuser"], False)
        self.assertEqual(attributes["last_login"], None)

        self.assertEqual(attributes["first_name"], "Paolino")
        self.assertEqual(attributes["last_name"], "Paperino")
        self.assertEqual(attributes["shoe_size"], 14)

    def test_user_signup_existing(self):
        # create test user
        url = reverse("api:user-signup")
        response = self.client.post(url, TEST_USER_WITH_PASSWORD, format="json")  # NO AUTH TOKEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # post again but this time the user already exists
        response = self.client.post(url, TEST_USER, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_signin_use_session_signout(self):
        # create test user first
        url = reverse("api:user-signup")
        response = self.client.post(url, TEST_USER_WITH_PASSWORD, format="json")  # NO AUTH TOKEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # then try logging in
        url = reverse("api:user-signin")
        self.client.login(username=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = response.data
        self.assertEqual(user["type"], TYPE_PREFIX + USER_TYPE)
        self.assertEqual(user["id"], TEST_USER_EMAIL)
        attributes = user["attributes"]
        self.assertTrue("password" not in attributes)
        self.assertEqual(attributes["first_name"], "Paolino")
        self.assertEqual(attributes["last_name"], "Paperino")
        self.assertEqual(attributes["is_staff"], False)
        self.assertEqual(attributes["is_superuser"], False)

        # retrieve again using session credentials
        url = reverse("api:user-me")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # sign out of current session
        url = reverse("api:user-signout")
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # retrieve again with missing session credentials
        url = reverse("api:user-me")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
