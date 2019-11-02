from analitico import TYPE_PREFIX, USER_TYPE
from django.urls import reverse
from rest_framework import status
from .utils import AnaliticoApiTestCase

import analitico
from api.models import Role, Job, Dataset, Model, Recipe, Endpoint, Log, Token, User, Notebook, Workspace

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

    def test_permissions_setting_to_owned_workspace(self):
        self.auth_token(self.token1)
        url = reverse("api:workspace-detail", args=("ws_001",))

        # GET the workspace as it is now, no permissions specified
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.data

        # POST on specific workspace should not work
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 405)

        # PATCH with no changes
        response = self.client.patch(url, data=data)
        self.assertEqual(response.status_code, 200)

        # PUT with no changes
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)

        # PUT with new roles and permissions for user2@analitico.ai
        data = response.data
        data["attributes"]["permissions"] = {
            "user2@analitico.ai": {"roles": ["role1", "role2"], "permissions": ["permission1", "permission2"]}
        }
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(len(data["attributes"]["permissions"].keys()), 1)
        self.assertEqual(len(data["attributes"]["permissions"]["user2@analitico.ai"]["roles"]), 2)
        self.assertEqual(data["attributes"]["permissions"]["user2@analitico.ai"]["roles"][0], "role1")
        self.assertEqual(data["attributes"]["permissions"]["user2@analitico.ai"]["roles"][1], "role2")
        self.assertEqual(len(data["attributes"]["permissions"]["user2@analitico.ai"]["permissions"]), 2)
        self.assertEqual(data["attributes"]["permissions"]["user2@analitico.ai"]["permissions"][0], "permission1")
        self.assertEqual(data["attributes"]["permissions"]["user2@analitico.ai"]["permissions"][1], "permission2")

        # PATCH with new roles and permissions for user3@analitico.ai
        data = response.data
        data["attributes"]["permissions"] = {
            "user3@analitico.ai": {"roles": ["role1a", "role2a"], "permissions": ["permission1a", "permission2a"]}
        }
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(len(data["attributes"]["permissions"].keys()), 1)
        self.assertEqual(len(data["attributes"]["permissions"]["user3@analitico.ai"]["roles"]), 2)
        self.assertEqual(data["attributes"]["permissions"]["user3@analitico.ai"]["roles"][0], "role1a")
        self.assertEqual(data["attributes"]["permissions"]["user3@analitico.ai"]["roles"][1], "role2a")
        self.assertEqual(len(data["attributes"]["permissions"]["user3@analitico.ai"]["permissions"]), 2)
        self.assertEqual(data["attributes"]["permissions"]["user3@analitico.ai"]["permissions"][0], "permission1a")
        self.assertEqual(data["attributes"]["permissions"]["user3@analitico.ai"]["permissions"][1], "permission2a")

        # PATCH permissions for multiple users
        data = response.data
        data["attributes"]["permissions"] = {
            "user2@analitico.ai": {"roles": ["role1a", "role2a"], "permissions": ["permission1a", "permission2a"]},
            "user3@analitico.ai": {"roles": ["role1a"]},
            "user4@analitico.ai": {"permissions": ["permission1a", "permission2a", "permission3a"]},
        }
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(len(data["attributes"]["permissions"].keys()), 3)
        # user2
        self.assertEqual(len(data["attributes"]["permissions"]["user2@analitico.ai"]["roles"]), 2)
        self.assertEqual(data["attributes"]["permissions"]["user2@analitico.ai"]["roles"][0], "role1a")
        self.assertEqual(data["attributes"]["permissions"]["user2@analitico.ai"]["roles"][1], "role2a")
        self.assertEqual(len(data["attributes"]["permissions"]["user2@analitico.ai"]["permissions"]), 2)
        self.assertEqual(data["attributes"]["permissions"]["user2@analitico.ai"]["permissions"][0], "permission1a")
        self.assertEqual(data["attributes"]["permissions"]["user2@analitico.ai"]["permissions"][1], "permission2a")
        # user3
        self.assertEqual(len(data["attributes"]["permissions"]["user3@analitico.ai"]["roles"]), 1)
        self.assertEqual(data["attributes"]["permissions"]["user3@analitico.ai"]["roles"][0], "role1a")
        self.assertEqual(data["attributes"]["permissions"]["user3@analitico.ai"]["permissions"], None)
        # user4
        self.assertEqual(len(data["attributes"]["permissions"]["user4@analitico.ai"]["permissions"]), 3)
        self.assertEqual(data["attributes"]["permissions"]["user4@analitico.ai"]["permissions"][0], "permission1a")
        self.assertEqual(data["attributes"]["permissions"]["user4@analitico.ai"]["permissions"][1], "permission2a")
        self.assertEqual(data["attributes"]["permissions"]["user4@analitico.ai"]["permissions"][2], "permission3a")

    def test_permissions_setting_to_someone_elses_workspace(self):
        url = reverse("api:workspace-detail", args=("ws_002",))
        # this is a long story so bear with me...

        # user2 has a workspace all of his own
        self.auth_token(self.token2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        ws2 = response.data
        self.assertEqual(ws2["attributes"]["title"], "Workspace2")

        # user3 cannot see the workspace
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # user2 gives access to user3 in read/write mode so user3 can see the workspace
        self.auth_token(self.token2)
        ws2["attributes"]["permissions"] = {"user3@analitico.ai": {"roles": ["analitico.reader", "analitico.editor"]}}
        response = self.client.put(url, data=ws2)
        self.assertEqual(response.status_code, 200)

        # user3 can now see the workspace
        self.auth_token(self.token3)
        response = self.client.get(url)
        ws2 = response.data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ws2["attributes"]["title"], "Workspace2")

        # user3 is allowed to change the title of the workspace
        self.auth_token(self.token3)
        data = {"attributes": {"title": "New title by user3"}}
        response = self.client.patch(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["attributes"]["title"], "New title by user3")

        # user3 trying to change permissions on the workspace and cannot do that
        self.auth_token(self.token3)
        ws2["attributes"]["permissions"] = {"user4@analitico.ai": {"roles": ["analitico.reader", "analitico.editor"]}}
        response = self.client.put(url, data=ws2)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # user2 gives super admin rights on his workspace to user3
        self.auth_token(self.token2)
        ws2["attributes"]["permissions"] = {
            "user3@analitico.ai": {"roles": ["analitico.reader", "analitico.editor", "analitico.admin"]}
        }
        response = self.client.put(url, data=ws2)
        self.assertEqual(response.status_code, 200)

        # user3 can now change permissions on the workspace and add user4
        self.auth_token(self.token3)
        ws2["attributes"]["permissions"] = {"user4@analitico.ai": {"roles": ["analitico.reader", "analitico.editor"]}}
        response = self.client.put(url, data=ws2)
        self.assertEqual(response.status_code, 200)

        # user3 now locked himself out of the workspace
        self.auth_token(self.token3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # but user4 is out having a beer, will be back next year...
        self.auth_token(self.token4)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

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
        response = self.client.post(url, {"workspace": "ws_001", "title": "Created by reader3"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # analitico.reader CANNOT post dataset
        role.roles = "role1,role2,analitico.reader,role3"
        role.save()
        response = self.client.post(url, {"workspace": "ws_001", "title": "Created by reader3"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # analitico.editor can post dataset
        role.roles = "role1,role2,analitico.editor,role3"
        role.save()
        response = self.client.post(url, {"workspace": "ws_001", "title": "Created by editor3"}, format="json")
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

    ##
    ## Gallery
    ##

    def test_permissions_gallery(self):
        # regular user can retrieve gallery specifically
        self.auth_token(self.token2)
        url = reverse("api:workspace-detail", args=(self.ws_gallery.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["id"], "ws_gallery")
        self.assertEqual(data["attributes"]["title"], "Gallery Workspace")
        # regular user CANNOT alter gallery
        data["attributes"]["title"] = "New Gallery"
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, 404)
        # regular user CANNOT delete gallery
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
        # gallery is still there
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # check permissions on regular items in the gallery
        for item_class in (Dataset, Recipe, Notebook):
            item = item_class(workspace=self.ws_gallery)
            item.save()

            item_url = reverse(f"api:{item.type}-detail", args=(item.id,))

            response = self.client.get(item_url)
            self.assertEqual(response.status_code, 200)  # can GET
            response = self.client.put(item_url, data)
            self.assertEqual(response.status_code, 404)  # can't PUT
            response = self.client.put(item_url, data)
            self.assertEqual(response.status_code, 404)  # can't DELETE
            response = self.client.get(item_url)
            self.assertEqual(response.status_code, 200)  # still there

