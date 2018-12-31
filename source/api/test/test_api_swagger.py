
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
        self.assertEqual(data['consumes'][0], 'application/json')
        self.assertEqual(data['produces'][0], 'application/json')


    def test_api_swagger_ui(self):
        """ Check swagger UI page with API documentation """
        url = reverse('api-docs')
        response = self.client.get(url)

        self.assertEqual(response.status_text, 'OK')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<title>Analitico API</title>')
