
import os
import os.path

import rest_framework.test
from rest_framework import status

from django.urls import reverse

from api.models import Project, Token, Call, User

from analitico.utilities import read_json, get_dict_dot

# pylint: disable=no-member


ASSETS_PATH = os.path.dirname(os.path.realpath(__file__)) + '/assets/'

class APITestCase(rest_framework.test.APITestCase):
    """ Base class for testing analitico APIs """

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


    def auth_token(self, token=None):
        """ Append authorization token to self.client calls """        
        if token is not None:
            self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token.id)
        else:
            self.client.logout()


    def setup_basics(self):
        self.user1 = User.objects.create_user(email='user1@analitico.ai', is_superuser=True) # 1st user is admin
        self.user2 = User.objects.create_user(email='user2@analitico.ai') # 2nd is a regular user
        self.user3 = User.objects.create_user(email='user3@analitico.ai') # 3rd is a regular user

        self.token1 = Token.objects.create(pk='tok_user1', user=self.user1)
        self.token2 = Token.objects.create(pk='tok_user2', user=self.user2)
        self.token3 = Token.objects.create(pk='tok_user3', user=self.user3)


    def setUp(self):
        """ Prepare test users with test auth tokens """
        self.setup_basics()
