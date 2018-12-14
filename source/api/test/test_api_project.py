
from django.test import TestCase
from rest_framework.test import APITestCase
from api.models import Project

# pylint: disable=no-member

PRJ_SETTINGS = {
    'data': {
        'parameters': {
            'learning_rate': 0.50,
            'iterations': 30
        }
    }
}

class ProjectsApiTests(APITestCase):

    def setUp(self):
        Project.objects.create(id='s24-order-time', settings=PRJ_SETTINGS)

    def test_project_model_with_existing_project(self):
        prj1 = Project.objects.get(pk='s24-order-time')
        self.assertIsNotNone(prj1)
        self.assertEqual(prj1.settings['data']['parameters']['learning_rate'], 0.50)
        self.assertEqual(prj1.settings['data']['parameters']['iterations'], 30)

    def test_project_api_with_existing_project(self):
        response = self.client.get('/api/v1/project/s24-order-time/', format='json')
        self.assertIsNotNone(response.data)
        settings = response.data['data']['settings']['data']
        self.assertIsNotNone(settings)
        self.assertEqual(settings['parameters']['learning_rate'], 0.50)
        self.assertEqual(settings['parameters']['iterations'], 30)

    def test_project_api_with_missing_project(self):
        response = self.client.get('/api/v1/project/fake-id/', format='json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.reason_phrase, 'Not Found')
        self.assertEqual(response.data['error']['status'], '404')

