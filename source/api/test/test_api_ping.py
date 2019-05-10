from django.test import TestCase
from .utils import AnaliticoApiTestCase


class PingApiTests(AnaliticoApiTestCase):
    def OFFtest_api_ping(self):
        response = self.client.post("/api/ping", {"test1": "value1", "test2": "value2"}, format="json")
        self.assertIsNotNone(response.data)
        self.assertIsNotNone(response.data["data"])
        self.assertEqual(response.data["data"]["test1"], "value1")
        self.assertEqual(response.data["data"]["test2"], "value2")

    def test_api_404(self):
        response = self.client.post("/api/fake_endpoint", {"test1": "value1", "test2": "value2"}, format="json")
        self.assertEqual(response.reason_phrase, "Not Found")
        self.assertEqual(response.status_code, 404)
