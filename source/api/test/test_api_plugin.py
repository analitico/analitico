from django.urls import reverse
from rest_framework import status

from .utils import AnaliticoApiTestCase
from api.factory import factory

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class PluginTests(AnaliticoApiTestCase):
    """ Test the plugin APIs (not the plugins themselves which are tested in analitico.plugin) """

    def test_plugin_list(self):
        url = reverse("api:plugin-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        plugins = factory.get_plugins()
        self.assertEqual(len(plugins), len(data))

        for i, plugin in enumerate(plugins):
            self.assertEqual(data[i]["attributes"]["name"], plugin)
