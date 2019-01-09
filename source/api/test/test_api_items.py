
from django.test import TestCase
from rest_framework.test import APITestCase
from api.models import Token, Call, User

import api.models

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

class ItemsTests(APITestCase):

    def setUp(self):
        try:
            self.user1 = User.objects.create_user(email='uploader1@analitico.ai')
            self.user2 = User.objects.create_user(email='uploader2@analitico.ai')

            self.token1 = Token.objects.create(pk='tok_uploader1', user=self.user1)
            self.token1.user = self.user1
            self.token1.save()
            self.token2 = Token.objects.create(pk='tok_uploader2')
            self.token2.user = self.user2
            self.token2.save()

            self.prj1 = api.models.Project.objects.create(pk='up-prj-001')
            self.prj1.owner = self.user1
            self.prj1.save()
            self.prj2 = api.models.Project.objects.create(pk='up-prj-002')
            self.prj2.owner = self.user2
            self.prj2.save()
        except Exception as exc:
            print(exc)
            raise exc


    def test_items_default_id_prefix(self):
        """ Test models to make sure they are created with the correct prefix in their IDs """
        item = api.models.Workspace()
        self.assertTrue(item.id.startswith(api.models.WORKSPACE_PREFIX))

        item = api.models.Dataset()
        self.assertTrue(item.id.startswith(api.models.DATASET_PREFIX))

        item = api.models.Recipe()
        self.assertTrue(item.id.startswith(api.models.RECIPE_PREFIX))

        item = api.models.Model()
        self.assertTrue(item.id.startswith(api.models.MODEL_PREFIX))

        item = api.models.Service()
        self.assertTrue(item.id.startswith(api.models.SERVICE_PREFIX))

