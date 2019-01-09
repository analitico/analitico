
import os

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from analitico.utilities import read_json, get_dict_dot

import api.models
import api.test

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + '/assets/'

class ItemsTests(api.test.APITestCase):

    def read_json_asset(self, path):
        abs_path = os.path.join(ASSETS_PATH, path)
        return read_json(abs_path)


    def get_item(self, item_type, item_id, token=None, status_code=status.HTTP_200_OK):
        url = reverse('api:' + item_type + '-detail', args=(item_id,))
        self.auth_token(token)
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status_code)
        if response.status_code == status.HTTP_200_OK:
            self.assertIsNotNone(response.data)
        return response.data


    def patch_item(self, item_type, item_id, item, token=None, status_code=status.HTTP_200_OK):
        url = reverse('api:' + item_type + '-detail', args=(item_id,))
        self.auth_token(token)
        response = self.client.patch(url, item, format='json')
        self.assertEqual(response.status_code, status_code)
        return response.data


    def delete_item(self, item_type, item_id, token=None, status_code=status.HTTP_200_OK):
        url = reverse('api:' + item_type + '-detail', args=(item_id,))
        self.auth_token(token)
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status_code)
        return response.data


    def upload_items(self, endpoint, prefix):
        for path in os.listdir(ASSETS_PATH):
            if path.startswith(prefix):
                item = self.read_json_asset(path)

                token = self.token1
                if (get_dict_dot(item, 'attributes.user') == 'user2@analitico.ai'):
                    token = self.token2
                if (get_dict_dot(item, 'attributes.user') == 'user3@analitico.ai'):
                    token = self.token3

                self.auth_token(token)
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
        self.assertEqual(item['attributes']['user'], 'user1@analitico.ai')
        self.assertEqual(item['attributes']['title'], 'This is the title')
        self.assertEqual(item['attributes']['description'], 'This is the description')


    def test_workspace_get_user2(self):
        item = self.get_item('workspace', 'ws_002', self.token1)
        self.assertEqual(item['id'], 'ws_002')
        self.assertEqual(item['attributes']['user'], 'user2@analitico.ai')
        self.assertEqual(item['attributes']['title'], 'This is the title')
        self.assertEqual(item['attributes']['description'], 'This is the description')


    def test_workspace_get_without_authorization(self):
        # user2 is not the owner of this workspace so, altough it does exist,
        # the server should pretend it's not there (which it isn't for this user)
        # and return an item not found code of HTTP 404
        item = self.get_item('workspace', 'ws_001', self.token2, status_code=status.HTTP_404_NOT_FOUND)
        self.assertEqual(item['error']['code'], 'Not Found')
        self.assertIsNotNone(item['error']['detail'])
        self.assertEqual(item['error']['status'], '404') # a string, not a number


    def test_workspace_get_without_authorization_as_admin(self):
        # ws_002 is owned by user2@analitico.ai but user1 is an admin so he should get it
        item = self.get_item('workspace', 'ws_002', self.token1)
        self.assertEqual(item['id'], 'ws_002')
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


    def test_workspace_patch_title_user2(self):
        item = self.get_item('workspace', 'ws_002', self.token1)
        self.assertEqual(item['id'], 'ws_002')
        self.assertEqual(item['attributes']['title'], 'This is the title')
        self.assertEqual(item['attributes']['description'], 'This is the description')

        patch = {
            'data': {
                'id': 'ws_002',
                'attributes': {
                    'title': 'This is the patched title'
                }
            }
        }
        patch_item = self.patch_item('workspace', 'ws_002', patch, self.token1)        
        self.assertEqual(patch_item['attributes']['title'], 'This is the patched title')
        self.assertEqual(patch_item['attributes']['description'], 'This is the description')


    def test_workspace_patch_item_patch_title_without_authorization(self):
        patch = {
            'data': {
                'id': 'ws_001',
                'attributes': {
                    'title': 'This is the patched title'
                }
            }
        }
        # user2 is not the owner of this workspace so, altough it does exist,
        # the server should pretend it's not there (which it isn't for this user)
        # and return an item not found code of HTTP 404
        patch_item = self.patch_item('workspace', 'ws_001', patch, self.token2, status_code=status.HTTP_404_NOT_FOUND)    
        self.assertEqual(patch_item['error']['code'], 'Not Found')
        self.assertIsNotNone(patch_item['error']['detail'])
        self.assertEqual(patch_item['error']['status'], '404') # a string, not a number


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


    def test_workspace_patch_made_up_attribute_with_children(self):
        item = self.get_item('workspace', 'ws_001', self.token1)
        self.assertEqual(item['id'], 'ws_001')
        self.assertEqual(item['attributes']['title'], 'This is the title')
        self.assertEqual(item['attributes']['description'], 'This is the description')
        self.assertFalse('made_up_attribute' in item['attributes'])

        patch = {
            'data': {
                'id': 'ws_001',
                'attributes': {
                    'made_up_attribute_two': {
                        'child1': 'This is a made up attribute, child 1',
                        'child2': 'This is a made up attribute, child 2',
                    }, 
                    'made_up_attribute_three': 'This is made_up_attribute_three'
                }
            }
        }
        patch_item = self.patch_item('workspace', 'ws_001', patch, self.token1)        
        self.assertEqual(patch_item['attributes']['title'], 'This is the title')
        self.assertEqual(patch_item['attributes']['description'], 'This is the description')
        self.assertEqual(patch_item['attributes']['made_up_attribute_two']['child1'], 'This is a made up attribute, child 1')
        self.assertEqual(patch_item['attributes']['made_up_attribute_two']['child2'], 'This is a made up attribute, child 2')
        self.assertEqual(patch_item['attributes']['made_up_attribute_three'], 'This is made_up_attribute_three')


    def test_workspace_patch_change_remove(self):
        patch = {
            'data': {
                'id': 'ws_001',
                'attributes': {
                    'made_up_attribute': 'adding something'
                }
            }
        }
        patch_item = self.patch_item('workspace', 'ws_001', patch, self.token1)        
        self.assertEqual(patch_item['attributes']['made_up_attribute'], 'adding something')

        patch['data']['attributes']['made_up_attribute'] = 'then changing it'
        patch_item = self.patch_item('workspace', 'ws_001', patch, self.token1)        
        self.assertEqual(patch_item['attributes']['made_up_attribute'], 'then changing it')

        patch['data']['attributes']['made_up_attribute'] = None # them removing it
        patch_item = self.patch_item('workspace', 'ws_001', patch, self.token1)        
        self.assertIsNone(patch_item['attributes']['made_up_attribute'])


    def test_workspace_delete(self):
        item = self.delete_item('workspace', 'ws_001', self.token1, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(item)

        # no try and get deleted item, should return a 404
        item = self.delete_item('workspace', 'ws_001', self.token1, status.HTTP_404_NOT_FOUND)
        self.assertEqual(item['error']['code'], 'Not Found')
        self.assertIsNotNone(item['error']['detail'])
        self.assertEqual(item['error']['status'], '404') # a string, not a number


    def test_workspace_delete_without_authorization(self):
        # user2 is not the owner of this workspace so, altough it does exist,
        # the server should pretend it's not there (which it isn't for this user)
        # and return an item not found code of HTTP 404
        item = self.delete_item('workspace', 'ws_001', self.token2, status_code=status.HTTP_404_NOT_FOUND)
        self.assertEqual(item['error']['code'], 'Not Found')
        self.assertIsNotNone(item['error']['detail'])
        self.assertEqual(item['error']['status'], '404') # a string, not a number


    def test_workspace_delete_without_authorization_as_admin(self):
        # ws_002 is owned by user2@analitico.ai but user1 is an admin so he should be able to delete it
        item = self.delete_item('workspace', 'ws_002', token=self.token1, status_code=status.HTTP_204_NO_CONTENT)
        self.assertIsNone(item)






