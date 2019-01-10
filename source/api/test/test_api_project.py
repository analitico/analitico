
import rest_framework.test
import api.test

from django.urls import reverse
from django.test import TestCase

from api.models import Project, Token, Call, User

# pylint: disable=no-member

PRJ_SETTINGS = {
    'data': {
        'parameters': {
            'learning_rate': 0.50,
            'iterations': 30
        }
    }
}


class ProjectsApiTests(api.test.APITestCase):

    def setUp(self):
        super().setUp()
        self.project1 = Project.objects.create(id='test-project1', settings=PRJ_SETTINGS, owner=self.user1)


    def test_project_api_with_existing_project(self):
        self.auth_token(self.token1)
        response = self.client.get('/api/v1/projects/test-project1', format='json')
        self.assertIsNotNone(response.data)
        settings = response.data['settings']
        self.assertIsNotNone(settings)
        self.assertEqual(settings['data']['parameters']['learning_rate'], PRJ_SETTINGS['data']['parameters']['learning_rate'])
        self.assertEqual(settings['data']['parameters']['iterations'], PRJ_SETTINGS['data']['parameters']['iterations'])


    def test_project_api_with_existing_project_no_token(self):
        self.auth_token()
        response = self.client.get('/api/v1/projects/s24-order-time', format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.status_text, 'Unauthorized')
        self.assertEqual(response.data['error']['code'], 'not_authenticated')


    def test_project_api_with_missing_project(self):
        self.auth_token(self.token1)
        response = self.client.get('/api/v1/projects/fake-id', format='json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.reason_phrase, 'Not Found')
        self.assertEqual(response.data['error']['code'], 'Not Found')
        self.assertEqual(response.data['error']['status'], '404')


    def test_project_api_with_missing_project_no_token(self):
        self.auth_token()
        response = self.client.get('/api/v1/projects/fake-id', format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.reason_phrase, 'Unauthorized')
        self.assertEqual(response.data['error']['code'], 'not_authenticated')
        self.assertEqual(response.data['error']['status'], '401')
