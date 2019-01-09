
import os

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from analitico.utilities import read_json

import api.models
import api.test

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + '/assets/'

class ItemsTests(api.test.APITestCase):

    def read_json_asset(self, path):
        abs_path = os.path.join(ASSETS_PATH, path)
        return read_json(abs_path)


    def get_item(self, item_type, item_id, token=None):
        url = reverse('api:' + item_type + '-detail', args=(item_id,))
        self.auth_token(self.token1)
        response = self.client.get(url, format='json')
        self.assertIsNotNone(response.data)
        return response.data


    def patch_item(self, item_type, item_id, item, token=None):
        url = reverse('api:' + item_type + '-detail', args=(item_id,))
        self.auth_token(self.token1)
        response = self.client.patch(url, item, format='json')
        return response.data


    def upload_items(self, endpoint, prefix):
        for path in os.listdir(ASSETS_PATH):
            if path.startswith(prefix):
                item = self.read_json_asset(path)
                self.auth_token(self.token1)
                response = self.client.post(endpoint, { 'data': item }, format='json')
                self.assertIsNotNone(response.data)

                created_item = response.data
                self.assertEqual(item['id'], created_item['id'])
                self.assertEqual(item['type'], created_item['type'])
                self.assertEqual(item['attributes']['title'], created_item['attributes']['title'])
                self.assertEqual(item['attributes']['description'], created_item['attributes']['description'])


    def setUp(self):
        self.setup_basics()
        try: 
            url = reverse('api:workspace-list')
            self.upload_items(url, api.models.WORKSPACE_PREFIX)

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


    ##
    ## Workspace
    ##

    def test_workspace_get(self):
        item = self.get_item('workspace', 'ws_001', self.token1)
        self.assertEqual(item['id'], 'ws_001')
        self.assertEqual(item['attributes']['title'], 'This is the title')
        self.assertEqual(item['attributes']['description'], 'This is the description')


    def test_workspace_patch_title(self):
        item = self.get_item('workspace', 'ws_001', self.token1)
        self.assertEqual(item['id'], 'ws_001')
        self.assertEqual(item['attributes']['title'], 'This is the title')
        self.assertEqual(item['attributes']['description'], 'This is the description')

        patch = {
            'data': {
                'id': 'ws_001',
                'attributes': {
                    'title': 'This is the patched title'
                }
            }
        }
        patch_item = self.patch_item('workspace', 'ws_001', patch, self.token1)        
        self.assertEqual(patch_item['attributes']['title'], 'This is the patched title')
        self.assertEqual(patch_item['attributes']['description'], 'This is the description')



    def test_workspace_patch_made_up_attribute(self):
        item = self.get_item('workspace', 'ws_001', self.token1)
        self.assertEqual(item['id'], 'ws_001')
        self.assertEqual(item['attributes']['title'], 'This is the title')
        self.assertEqual(item['attributes']['description'], 'This is the description')
        self.assertFalse('made_up_attribute' in item['attributes'])

        patch = {
            'data': {
                'id': 'ws_001',
                'attributes': {
                    'made_up_attribute': 'This is a made up attribute'
                }
            }
        }
        patch_item = self.patch_item('workspace', 'ws_001', patch, self.token1)        
        self.assertEqual(patch_item['attributes']['title'], 'This is the title')
        self.assertEqual(patch_item['attributes']['description'], 'This is the description')
        self.assertEqual(patch_item['attributes']['made_up_attribute'], 'This is a made up attribute')

