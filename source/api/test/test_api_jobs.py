import os
import os.path
import json

from django.urls import reverse
from rest_framework import status

# conflicts with django's dynamically generated model.objects

# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

from analitico import *
from analitico.status import *
from analitico.constants import ACTION_PROCESS
from analitico.utilities import read_json

from api.models import *
from api.factory import factory
from api.models.log import *
from api.pagination import *

from .utils import AnaliticoApiTestCase


class JobsTests(AnaliticoApiTestCase):
    """ Test jobs operations via APIs (inherit from notebooks so we can do jobs on notebooks easily) """

    def test_job_notebook_process(self):
        response = self.post_notebook("notebook10.ipynb", "nb_01")

        # if we process a notebook a job is produced
        url = reverse("api:notebook-job-action", args=("nb_01", ACTION_PROCESS))
        response = self.client.post(url)
        job = response.data

        self.assertEqual(job["type"], "analitico/job")
        self.assertTrue(job["id"].startswith(JOB_PREFIX))
        self.assertEqual(job["attributes"]["status"], STATUS_CREATED)

        # there is only one job in the list
        url = reverse("api:job-list")
        jobs = self.get_items(JOB_TYPE, self.token1)

        self.assertEqual(len(jobs), 1)
