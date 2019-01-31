from django.test import TestCase
from rest_framework.test import APITestCase
from api.models import Token, Call, User
import api.models

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member


class ProjectUploadApiTests(APITestCase):
    def setUp(self):
        try:
            self.user1 = User.objects.create_user(email="uploader1@analitico.ai")
            self.user2 = User.objects.create_user(email="uploader2@analitico.ai")

            self.token1 = Token.objects.create(pk="tok_uploader1", user=self.user1)
            self.token1.user = self.user1
            self.token1.save()
            self.token2 = Token.objects.create(pk="tok_uploader2")
            self.token2.user = self.user2
            self.token2.save()

            self.prj1 = api.models.Project.objects.create(pk="up-prj-001")
            self.prj1.owner = self.user1
            self.prj1.save()
            self.prj2 = api.models.Project.objects.create(pk="up-prj-002")
            self.prj2.owner = self.user2
            self.prj2.save()
        except Exception as exc:
            print(exc)
            raise exc

    def test_api_upload_no_post(self):
        response = self.client.post("/api/project/up-prj-001/upload/test001.csv", format="json")
        self.assertEqual(response.status_code, 405)
        error = response.data["error"]
        self.assertEqual(error["status"], "405")

    def test_api_upload_no_get(self):
        response = self.client.get("/api/project/up-prj-001/upload/test001.csv", format="json")
        self.assertEqual(response.status_code, 405)
        error = response.data["error"]
        self.assertEqual(error["status"], "405")

    def test_api_404(self):
        response = self.client.post("/api/fake_endpoint", {"test1": "value1", "test2": "value2"}, format="json")
        self.assertEqual(response.reason_phrase, "Not Found")
        self.assertEqual(response.status_code, 404)
