from analitico import TYPE_PREFIX, USER_TYPE
from django.urls import reverse
from rest_framework import status
from .utils import AnaliticoApiTestCase

import analitico
from api.models import Role, Job, Dataset, Model, Recipe, Endpoint, Log, Token, User, Notebook

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class PermissionsTests(AnaliticoApiTestCase):
    """ Test granular API roles and permissions """

    def editor_role_tests_by_item_class(self, item_class, item_prefix, item_type):
        # item belong to ws1 which belongs to user1
        for i in range(0, 20):
            item = item_class(workspace=self.ws1, id=f"{item_prefix}ws1_{i}")
            item.save()
        for i in range(0, 10):
            item = item_class(workspace=self.ws2, id=f"{item_prefix}ws2_{i}")
            item.save()
        for i in range(0, 5):
            item = item_class(workspace=self.ws3, id=f"{item_prefix}ws3_{i}")
            item.save()

        # user is an analitico.reader and can read
        self.auth_token(self.token3)
        role = Role(workspace=self.ws1, user=self.user3)
        role.roles = "role1,role2,analitico.reader,role3"
        role.save()

        # can see his item and the ones of
        url = reverse(f"api:{item_type}-list") + "?sort=created_at"
        response = self.client.get(url, format="json")
        items = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(items), 20 + 5)

        # can GET specific item he owns
        item_id = items[23]["id"]
        url = reverse(f"api:{item_type}-detail", args=(item_id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], f"analitico/{item_type}")
        self.assertEqual(response.data["id"], item_id)

        # can GET specific item that user1 owns
        item_id = items[0]["id"]
        url = reverse(f"api:{item_type}-detail", args=(item_id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], f"analitico/{item_type}")
        self.assertEqual(response.data["id"], item_id)

        # can DELETE his own item
        url = reverse(f"api:{item_type}-detail", args=(items[23]["id"],))
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  # deleted

        # cannot DELETE other people's items
        item_id = items[0]["id"]
        url = reverse(f"api:{item_type}-detail", args=(item_id,))
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def setUp(self):
        self.setup_basics()

    ##
    ## Configurations
    ##

    def test_configurations_get(self):
        """ Retrieve static json with roles and permissions configurations """
        self.auth_token(self.token1)
        url = reverse("api:workspace-permissions")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        config = response.data

        self.assertIn("permissions", config)
        self.assertIn("roles", config)
        self.assertIn("analitico.reader", config["roles"])
        self.assertIn("analitico.editor", config["roles"])
        self.assertIn("analitico.admin", config["roles"])
        self.assertIn("analitico.datasets.get", config["permissions"])
        self.assertIn("analitico.datasets.create", config["permissions"])

    def test_configurations_get_without_auth(self):
        """ Retrieve static json with roles and permissions configurations WITHOUT a token """
        url = reverse("api:workspace-permissions")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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

    def test_roles_non_owner_with_read_role_on_jobs(self):
        self.editor_role_tests_by_item_class(Job, analitico.JOB_PREFIX, analitico.JOB_TYPE)

    def test_roles_non_owner_with_read_role_on_models(self):
        self.editor_role_tests_by_item_class(Model, analitico.MODEL_PREFIX, analitico.MODEL_TYPE)

    def test_roles_non_owner_with_read_role_on_datasets(self):
        self.editor_role_tests_by_item_class(Dataset, analitico.DATASET_PREFIX, analitico.DATASET_TYPE)

    def test_roles_non_owner_with_read_role_on_recipes(self):
        self.editor_role_tests_by_item_class(Recipe, analitico.RECIPE_PREFIX, analitico.RECIPE_TYPE)

    def test_roles_non_owner_with_read_role_on_endpoints(self):
        self.editor_role_tests_by_item_class(Endpoint, analitico.ENDPOINT_PREFIX, analitico.ENDPOINT_TYPE)

    def test_roles_non_owner_with_read_role_on_notebooks(self):
        self.editor_role_tests_by_item_class(Notebook, analitico.NOTEBOOK_PREFIX, analitico.NOTEBOOK_TYPE)

    def test_roles_non_owner_with_read_role_can_read_jobs_explicit_code(self):
        # jobs belong to ws1 which belongs to user1
        for i in range(0, 20):
            job = Job(workspace=self.ws1, id=f"jb_ws1_{i}")
            job.save()
        for i in range(0, 10):
            job = Job(workspace=self.ws2, id=f"jb_ws2_{i}")
            job.save()
        for i in range(0, 5):
            job = Job(workspace=self.ws3, id=f"jb_ws3_{i}")
            job.save()

        # user is an analitico.reader and can read
        self.auth_token(self.token3)
        role = Role(workspace=self.ws1, user=self.user3)
        role.roles = "role1,role2,analitico.reader,role3"
        role.save()

        # can see his jobs and the ones of
        url = reverse("api:job-list") + "?sort=created_at"
        response = self.client.get(url, format="json")
        jobs = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(jobs), 20 + 5)

        # can GET specific job he owns
        job_id = jobs[23]["id"]
        url = reverse("api:job-detail", args=(job_id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "analitico/job")
        self.assertEqual(response.data["id"], job_id)

        # can GET specific job that user1 owns
        job_id = jobs[0]["id"]
        url = reverse("api:job-detail", args=(job_id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "analitico/job")
        self.assertEqual(response.data["id"], job_id)

        # can DELETE his own job
        url = reverse("api:job-detail", args=(jobs[23]["id"],))
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  # deleted

        # cannot DELETE other people's jobs
        job_id = jobs[0]["id"]
        url = reverse("api:job-detail", args=(job_id,))
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_roles_non_owner_with_standard_role(self):
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

        # analitico.reader CANNOT delete
        role.roles = "role1,role2,analitico.reader,role3"
        role.save()
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # analitico.editor CAN delete
        role.roles = "role1,role2,analitico.editor"
        role.save()
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  # item deleted

        # analitico.editor CAN delete but notebook is no longer there
        role.roles = "analitico.editor,role3"
        role.save()
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # item no longer there

    def test_roles_reader_CANT_POST_editor_can(self):
        self.auth_token(self.token3)
        url = reverse("api:dataset-list")
        role = Role(workspace=self.ws1, user=self.user3)

        # no rights, no posting
        response = self.client.post(url, {"workspace": "ws_user1", "title": "Created by reader3"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # analitico.reader CANNOT post dataset
        role.roles = "role1,role2,analitico.reader,role3"
        role.save()
        response = self.client.post(url, {"workspace": "ws_user1", "title": "Created by reader3"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # analitico.editor can post dataset
        role.roles = "role1,role2,analitico.editor,role3"
        role.save()
        response = self.client.post(url, {"workspace": "ws_user1", "title": "Created by editor3"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_roles_reader_CANT_PATCH_editor_can(self):
        self.auth_token(self.token1)
        self.post_notebook("notebook01.ipynb", "nb_01")

        self.auth_token(self.token3)
        role = Role(workspace=self.ws1, user=self.user3)
        url = reverse("api:notebook-detail", args=("nb_01",))

        # analitico.editor can change title
        role.roles = "role1,role2,analitico.editor,role3"
        role.save()
        response = self.client.patch(url, {"title": "Title2"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
