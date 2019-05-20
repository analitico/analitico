from analitico import TYPE_PREFIX, USER_TYPE
from django.urls import reverse
from rest_framework import status
from .utils import AnaliticoApiTestCase

from api.models import Role

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class PermissionsTests(AnaliticoApiTestCase):
    """ Test granular API roles and permissions """

    def setUp(self):
        self.setup_basics()

    ##
    ## Configurations
    ##

    def test_permissions_get_configuration(self):
        """ Retrieve static json with roles and permissions configurations """
        url = reverse("api:workspace-permissions")
        response = self.client.get(url, format="json")

        config = response.data
        self.assertIn("permissions", config)
        self.assertIn("roles", config)
        self.assertIn("analitico.reader", config["roles"])
        self.assertIn("analitico.editor", config["roles"])
        self.assertIn("analitico.admin", config["roles"])
        self.assertIn("analitico.datasets.get", config["permissions"])
        self.assertIn("analitico.datasets.create", config["permissions"])

    ##
    ## Permissions
    ##

    def test_permissions_superuser_can_delete(self):
        self.auth_token(self.token1)
        self.post_notebook("notebook01.ipynb", "nb_01")

        url = reverse("api:notebook-detail", args=("nb_01",))
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_permissions_anonymous_cant_delete(self):
        self.auth_token(self.token1)
        self.post_notebook("notebook01.ipynb", "nb_01")

        url = reverse("api:notebook-detail", args=("nb_01",))
        self.auth_token(None)
        response = self.client.delete(url, format="json")
        # no credentials were provided, hence call is unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permissions_regular_user_with_custom_permission_can_delete(self):
        self.auth_token(self.token1)
        self.post_notebook("notebook01.ipynb", "nb_01")

        # create user role with custom permission
        role = Role(
            workspace=self.ws1,
            user=self.user3,
            permissions="permission1,permission2,analitico.notebooks.delete,permission3",
        )
        role.save()

        url = reverse("api:notebook-detail", args=("nb_01",))
        self.auth_token(self.token3)
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_permissions_non_owner_with_custom_permission(self):
        self.auth_token(self.token1)
        self.post_notebook("notebook01.ipynb", "nb_01")

        self.auth_token(self.token3)
        role = Role(workspace=self.ws1, user=self.user3)
        url = reverse("api:notebook-detail", args=("nb_01",))

        # user has the right custom permission
        role.permissions = "permission1,permission2,analitico.notebooks.get,permission3"
        role.save()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # user has the wrong custom permission
        role.permissions = "permission1,permission2,analitico.datasets.get,permission3"
        role.save()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # should be 403?

        # user has empty custom permission
        role.permissions = ""
        role.save()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # should be 403?

        # user has null custom permission
        role.permissions = None
        role.save()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # should be 403?

        # user has the custom permission to delete, not to get
        role.permissions = "permission1,permission2,analitico.notebooks.delete,permission3"
        role.save()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # should be 403?

        # user has the right custom permission
        role.permissions = "analitico.notebooks.get"
        role.save()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # user has the custom permission to delete
        role.permissions = "permission1,permission2,analitico.notebooks.delete,permission3"
        role.save()
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  # item deleted

        # user has the custom permission to delete
        role.permissions = "permission1,permission2,analitico.notebooks.delete,permission3"
        role.save()
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # item no longer there

    ##
    ## Roles
    ##

    def test_permissions_non_owner_with_standard_role(self):
        self.auth_token(self.token1)
        self.post_notebook("notebook01.ipynb", "nb_01")

        self.auth_token(self.token3)
        role = Role(workspace=self.ws1, user=self.user3)
        url = reverse("api:notebook-detail", args=("nb_01",))
        url_list = reverse("api:notebook-list")

        # user is an analitico.reader and can read
        role.roles = "role1,role2,analitico.reader,role3"
        role.save()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # user is an analitico.reader and can read but not delete
        role.roles = "role1,role2,analitico.reader,role3"
        role.save()
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # user is an analitico.editor and can delete
        role.roles = "role1,role2,analitico.editor"
        role.save()
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  # item deleted

        # user is an analitico.editor and can delete but notebook is no longer there
        role.roles = "analitico.editor,role3"
        role.save()
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # item no longer there
