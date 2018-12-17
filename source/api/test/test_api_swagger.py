
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

class SwaggerApiTests(APITestCase):

    def test_api_swagger_json(self):
        """ Check OpenAPI schema (formerly known as Swagger) """
        url = reverse('schema-json', args=['.json'])
        response = self.client.get(url, format='json')
        data = response.data

        self.assertIsNotNone(data)
        self.assertEqual(data['swagger'], '2.0')
        self.assertEqual(data['info']['title'], 'Analitico API')
        self.assertEqual(data['info']['contact']['email'], 'support@analitico.ai')
        self.assertEqual(data['basePath'], '/api/v1')
        self.assertEqual(data['consumes'][0], 'application/vnd.api+json')
        self.assertEqual(data['produces'][0], 'application/vnd.api+json')
