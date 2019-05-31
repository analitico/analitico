from django.urls import reverse
from rest_framework import status

# conflicts with django's dynamically generated model.objects
# pylint: disable=no-member

import api.models.log
from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import AnaliticoApiTestCase


class LogTests(AnaliticoApiTestCase):
    """ Test log operations like collecting logs and returning them as log entries via APIs """

    logger = factory.logger

    def setUp(self):
        self.setup_basics()

    def test_log_model(self):
        log = Log()
        log.id = "lg_001"
        log.save()

        logs = Log.objects.all()
        log_1 = logs[0]
        self.assertEqual(log_1.id, "lg_001")

    def test_log_basics(self):
        self.logger.info("info message")
        logs = Log.objects.all()

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].id[: len(analitico.LOG_PREFIX)], analitico.LOG_PREFIX)
        self.assertEqual(logs[0].title, "info message")

    def test_log_level(self):
        self.logger.debug("debug message")
        self.logger.info("info message")
        self.logger.warning("warning message")
        self.logger.error("error message")
        logs = Log.objects.all()

        # debug message was NOT logged to database
        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[1].level, logging.WARNING)
        self.assertEqual(logs[2].level, logging.ERROR)

    def test_log_formatting(self):
        self.logger.info("info message %d", 1)
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].level_name, "INFO")
        self.assertEqual(logs[0].title, "info message 1")
        self.assertEqual(logs[0].name, "analitico")

    def test_log_formatting_2(self):
        self.logger.info("info message %d, %s", 1, "pippo")
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].title, "info message 1, pippo")

    def test_log_formatting_plus_attrs(self):
        self.logger.info("info message %d, %s", 1, "mickey", more1="more_value")
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].title, "info message 1, mickey")
        self.assertEqual(logs[0].attributes["more1"], "more_value")

    def test_log_formatting_plus_recipe_1(self):
        """ Recipe model parameter is converted to recipe_id when stored in Log """
        recipe = Recipe()
        self.logger.info("info message %d, %s", 1, "mickey", recipe=recipe)
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].title, "info message 1, mickey")
        self.assertEqual(logs[0].attributes["recipe_id"], recipe.id)

    def test_log_formatting_plus_recipe_2(self):
        """ Recipe model parameter is converted to recipe_id when stored in Log and also added as item_id """
        recipe = Recipe()
        self.logger.info("info message %d, %s", 1, "mickey", recipe=recipe, item=recipe)
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].title, "info message 1, mickey")
        self.assertEqual(logs[0].item_id, recipe.id)
        self.assertEqual(logs[0].attributes["recipe_id"], recipe.id)

    def test_log_formatting_plus_items(self):
        """ Add various items to log and see them stored as item_id """
        workspace = Workspace()
        workspace.save()
        recipe = Recipe()
        recipe.workspace = workspace
        recipe.save()
        dataset = Dataset()
        dataset.workspace = workspace
        dataset.save()
        job = Job()
        job.workspace = workspace
        job.save()

        self.logger.info("info message %d, %s", 1, "mickey", recipe=recipe, item=recipe, job=job, dataset=dataset)
        logs = Log.objects.all()

        self.assertEqual(logs[0].level, logging.INFO)
        self.assertEqual(logs[0].title, "info message 1, mickey")
        self.assertEqual(logs[0].item_id, recipe.id)
        self.assertEqual(logs[0].job.id, job.id)

        self.assertEqual(logs[0].attributes["recipe_id"], recipe.id)
        self.assertEqual(logs[0].attributes["dataset_id"], dataset.id)

        # job_id should NOT be stored
        self.assertIsNone(logs[0].attributes.get("job_id", None))

    # TODO deprecate or restore logs rights
    def OFFtest_log_authorizations(self):
        """ Make sure each user can read logs of his own items, admins can read all logs """
        ws1 = Workspace()
        ws1.user = self.user1  # admin
        ws1.save()
        self.logger.info("Log something for workspace 1", item=ws1)

        ws2 = Workspace()
        ws2.user = self.user2  # regular user
        ws2.save()
        self.logger.info("Log something for workspace 2", item=ws2)

        ws4 = Workspace()
        ws4.user = self.user4  # staff user
        ws4.save()
        self.logger.info("Log something for workspace 4", item=ws4)

        # /api/logs endpoint

        self.auth_token(self.token1)  # admin reads all 3 logs
        url = reverse("api:log-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        self.auth_token()  # anon CANNOT read any logs
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.reason_phrase, "Unauthorized")
        self.assertEqual(response.data["error"]["code"], "not_authenticated")
        # NOTE: UNAUTHORIZED calls generate a django warning so now there are 4 logs!!

        self.auth_token(self.token4)  # staff user reads all 3 logs
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

        self.auth_token(self.token2)  # regular user reads only item assigned to his workspace
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["attributes"]["title"], "Log something for workspace 2")

        self.auth_token(self.token3)  # regular user reads only item assigned to his workspace, which is none
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # /api/workspaces/ws_xxx/logs

        self.auth_token()  # anon CANNOT read any logs
        url = reverse("api:workspace-log-list", args=(ws1.id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"]["code"], "not_authenticated")
        url = reverse("api:workspace-log-list", args=(ws2.id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"]["code"], "not_authenticated")

        self.auth_token(self.token1)  # admin reads single log attached to his workspace
        url = reverse("api:workspace-log-list", args=(ws1.id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["attributes"]["title"], "Log something for workspace 1")

        self.auth_token(self.token1)  # admin CAN read log for other workspace
        url = reverse("api:workspace-log-list", args=(ws2.id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["attributes"]["title"], "Log something for workspace 2")

        self.auth_token(self.token2)  # user CAN read log for his workspace
        url = reverse("api:workspace-log-list", args=(ws2.id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["attributes"]["title"], "Log something for workspace 2")

        self.auth_token(self.token2)  # user CANNOT read log for others' workspaces
        url = reverse("api:workspace-log-list", args=(ws4.id,))
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"]["code"], "not_found")

        # TODO decide if staff can read the workspace that ows the logs, currently only superuser can, not staff
        # self.auth_token(self.token4) # staff CAN read logs for other's workspaces
        # url = reverse("api:workspace-log-list", args=(ws2.id,))
        # response = self.client.get(url, format="json")
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(len(response.data), 1)
        # self.assertEqual(response.data[0]["attributes"]["title"], "Log something for workspace 2")
