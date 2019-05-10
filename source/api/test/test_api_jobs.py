from django.urls import reverse
from datetime import datetime, timedelta
from unittest import mock
from dateutil import parser

# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

import analitico
import api

from analitico import *
from analitico.status import STATUS_CREATED, STATUS_RUNNING, STATUS_CANCELED
from analitico.constants import ACTION_PROCESS
from rest_framework import status

from api.models import *
from api.models.job import *
from .utils import AnaliticoApiTestCase

# baseline date for tests faking cron based item scheduling
CRON_DATE = parser.parse("2020-04-17T00:00:00Z")


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

    ##
    ## Timeouts - jobs that have been "running" for a while should get cancelled
    ##

    def test_job_timeout_fresh(self):
        job1 = Job(workspace=self.ws1, status=STATUS_RUNNING)
        job1.save()

        # no timed out jobs
        timeouts = api.models.job.timeout_jobs()
        self.assertEqual(len(timeouts), 0)

    def test_job_timeout_stale(self):
        """ Test a job that's been running 10 minutes over the limit """
        # pretend we're in the past
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.utcnow() - timedelta(minutes=JOB_TIMEOUT_MINUTES + 10)
            job1 = Job(workspace=self.ws1, status=STATUS_RUNNING)
            job1.save()

        # should have 1 timed out job
        timeouts = api.models.job.timeout_jobs()
        self.assertEqual(len(timeouts), 1)
        self.assertEqual(job1.id, timeouts[0].id)
        self.assertEqual(timeouts[0].status, STATUS_CANCELED)

    def test_job_timeout_verystale(self):
        """ Test a job that's been running for a day """
        # pretend we're in the past
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.utcnow() - timedelta(days=1)
            job1 = Job(workspace=self.ws1, status=STATUS_RUNNING)
            job1.save()

        # should have 1 timed out job
        timeouts = api.models.job.timeout_jobs()
        self.assertEqual(len(timeouts), 1)
        self.assertEqual(job1.id, timeouts[0].id)
        self.assertEqual(timeouts[0].status, STATUS_CANCELED)

    def test_job_timeout_notquitestale(self):
        """ Test a job that's been running almost to the limit """
        # pretend we're in the past
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.utcnow() - timedelta(minutes=JOB_TIMEOUT_MINUTES - 1)
            job1 = Job(workspace=self.ws1, status=STATUS_RUNNING)
            job1.save()

        # should have no timed out jobs
        timeouts = api.models.job.timeout_jobs()
        self.assertEqual(len(timeouts), 0)

    def test_job_timeout_future(self):
        """ Test a job that's been scheduled for the future """
        # pretend we're in the future
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.utcnow() + timedelta(minutes=JOB_TIMEOUT_MINUTES)
            job1 = Job(workspace=self.ws1, status=STATUS_RUNNING)
            job1.save()

        # should have no timed out jobs
        timeouts = api.models.job.timeout_jobs()
        self.assertEqual(len(timeouts), 0)

    def test_job_timeout_future_date(self):
        """ Test a job that's been scheduled for a future date """
        # pretend we're in the future
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.utcnow() + timedelta(days=2)
            job1 = Job(workspace=self.ws1, status=STATUS_RUNNING)
            job1.save()

        # should have no timed out jobs
        timeouts = api.models.job.timeout_jobs()
        self.assertEqual(len(timeouts), 0)

    def test_job_timeout_stale_mix(self):
        """ Test a job that's been running 10 minutes over the limit """
        # fresh job
        job0 = Job(workspace=self.ws1, status=STATUS_RUNNING)
        job0.save()

        # stale job
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.utcnow() - timedelta(minutes=JOB_TIMEOUT_MINUTES + 10)
            job1 = Job(workspace=self.ws1, status=STATUS_RUNNING)
            job1.save()

        # old but not stale
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.utcnow() - timedelta(minutes=JOB_TIMEOUT_MINUTES - 5)
            job2 = Job(workspace=self.ws1, status=STATUS_RUNNING)
            job2.save()

        # should have 1 timed out job
        timeouts = api.models.job.timeout_jobs()
        self.assertEqual(len(timeouts), 1)
        self.assertEqual(job1.id, timeouts[0].id)
        self.assertEqual(timeouts[0].status, STATUS_CANCELED)

    ##
    ## Cron scheduling of jobs
    ##

    def schedule_mock(self, created_at=CRON_DATE, scheduled_at=CRON_DATE, tested_at=CRON_DATE, cron=None) -> [Job]:
        # create notebook that will be scheduled
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = created_at
            nb = Notebook(id="nb_01", workspace=self.ws1)
            if cron:
                schedule = {"cron": cron}
                if scheduled_at:
                    schedule["scheduled_at"] = scheduled_at.isoformat()
                nb.set_attribute("schedule", schedule)
            nb.save()

        # request scheduling and return jobs that were scheduled
        with mock.patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = tested_at
            url = reverse("api:job-schedule")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return response.data

    def test_job_schedule_none(self):
        """ Test not having a cron setting in the schedule """
        jobs = self.schedule_mock(cron="")
        self.assertEqual(len(jobs), 0)

    def test_job_schedule_every_minute_first(self):
        """ Test schedule that runs every minute, never run before """
        jobs = self.schedule_mock(scheduled_at=None, cron="* * * * *")
        self.assertEqual(len(jobs), 1)

    def test_job_schedule_every_minute_next(self):
        """ Test schedule that runs every minute but has run once already at this very same time """
        jobs = self.schedule_mock(cron="* * * * *")
        self.assertEqual(len(jobs), 0)

    def test_job_schedule_every_minute_future(self):
        """ Test schedule that runs every minute on the next minute """
        jobs = self.schedule_mock(tested_at=CRON_DATE + timedelta(minutes=1), cron="* * * * *")
        self.assertEqual(len(jobs), 1)

    def test_job_schedule_every_hour_1(self):
        jobs = self.schedule_mock(tested_at=CRON_DATE + timedelta(minutes=50), cron=CRON_EVERY_HOUR)
        self.assertEqual(len(jobs), 0)

    def test_job_schedule_every_hour_2(self):
        jobs = self.schedule_mock(tested_at=CRON_DATE + timedelta(minutes=60), cron=CRON_EVERY_HOUR)
        self.assertEqual(len(jobs), 1)

    def test_job_schedule_every_hour_3(self):
        jobs = self.schedule_mock(tested_at=CRON_DATE + timedelta(minutes=61), cron=CRON_EVERY_HOUR)
        self.assertEqual(len(jobs), 1)

    def test_job_schedule_every_hour_4(self):
        jobs = self.schedule_mock(tested_at=CRON_DATE + timedelta(days=1), cron=CRON_EVERY_HOUR)
        self.assertEqual(len(jobs), 1)

    def test_job_schedule_every_hour_already_run_1(self):
        """ Job runs every hour, last ran at 15 minutes, next due on the hour """
        jobs = self.schedule_mock(
            scheduled_at=CRON_DATE + timedelta(minutes=15),
            tested_at=CRON_DATE + timedelta(minutes=59),
            cron=CRON_EVERY_HOUR,
        )
        self.assertEqual(len(jobs), 0)

    def test_job_schedule_every_hour_already_run_2(self):
        """ Job runs every hour, last ran at 15 minutes, next due on the hour """
        jobs = self.schedule_mock(
            scheduled_at=CRON_DATE + timedelta(minutes=15),
            tested_at=CRON_DATE + timedelta(minutes=60),
            cron=CRON_EVERY_HOUR,
        )
        self.assertEqual(len(jobs), 1)

    def test_job_schedule_every_hour_already_run_3(self):
        """ Job runs every hour, last ran at 15 minutes, next due on the hour """
        jobs = self.schedule_mock(
            scheduled_at=CRON_DATE + timedelta(minutes=15),
            tested_at=CRON_DATE + timedelta(minutes=62),
            cron=CRON_EVERY_HOUR,
        )
        self.assertEqual(len(jobs), 1)

    def test_job_schedule_every_hour_already_run_4(self):
        jobs = self.schedule_mock(
            scheduled_at=CRON_DATE + timedelta(minutes=60),
            tested_at=CRON_DATE + timedelta(minutes=75),
            cron=CRON_EVERY_HOUR,
        )
        self.assertEqual(len(jobs), 0)

    def test_job_schedule_every_hour_already_run_5(self):
        jobs = self.schedule_mock(
            scheduled_at=CRON_DATE + timedelta(minutes=60),
            tested_at=CRON_DATE + timedelta(minutes=120),
            cron=CRON_EVERY_HOUR,
        )
        self.assertEqual(len(jobs), 1)

    def test_job_schedule_every_hour_already_run_6(self):
        jobs = self.schedule_mock(
            scheduled_at=CRON_DATE + timedelta(minutes=60),
            tested_at=CRON_DATE + timedelta(minutes=119),
            cron=CRON_EVERY_HOUR,
        )
        self.assertEqual(len(jobs), 0)
