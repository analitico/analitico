import os
import time
import logging
import datetime
import socket

from django.db import transaction
from analitico.constants import WORKER_TYPE, WORKER_PREFIX
from analitico.status import STATUS_CREATED, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED

from api.models import Job
from analitico.utilities import time_ms, get_runtime
from api.factory import ServerFactory, factory

from django.core.management.base import BaseCommand, CommandError

# Writing custom django-admin commands
# https://docs.djangoproject.com/en/2.1/howto/custom-management-commands/
# pylint: disable=no-member

WORKER_SUCCESS = 0  # generic success result
WORKER_ERROR = 100  # generic error code

POLLING_DELAY_SHORT = 0.500  # delay between succesfull queue polls
POLLING_DELAY_LONG = 5.0  # delay in case of errors


def generate_worker_id():
    now = datetime.datetime.utcnow()
    return WORKER_PREFIX + socket.gethostname() + now.strftime("_%Y%m%d%H%M%S")


class Command(BaseCommand):
    """ A django command used to run training jobs, either any pending ones or those specifically indicated """

    id = None

    help = "A worker for asynchrous jobs like pipeline processing, model training, etc."

    # TODO implement external quit signal?
    running = True

    def __init__(self, *args, **kwargs):
        self.id = generate_worker_id()

    def info(self, *args, **kwargs):
        factory.logger.info(*args, item=self, runtime=get_runtime(), **kwargs)

    def warning(self, *args, **kwargs):
        factory.logger.warning(*args, item=self, runtime=get_runtime(), **kwargs)

    def run_job(self, job) -> Job:
        """ Run job with given id """
        try:
            self.info("worker: %s, job: %s, action: %s", job.status, job.id, job.action, job=job)
            started_ms = time_ms()

            job.run(request=None, action=job.action)

            message = "worker: %s, job: %s, action: %s, elapsed: %dms"
            self.info(message, job.status, job.id, job.action, time_ms(started_ms), job=job)
            return job
        except Exception as e:
            self.warning("worker: %s, job: %s, action: %s", job.status, job.id, job.action, job=job, exception=e)
            raise e

    def get_pending_job(self, **options):
        # TODO use tags to further filter jobs
        # TODO order by time posted desc
        with transaction.atomic():
            # use select for update so that rows with selected jobs are
            # locked while we pick our job and change its status. this will
            # prevent other workers from taking this same job at the same time
            jobs = Job.objects.select_for_update().filter(status=STATUS_CREATED).order_by("created_at")
            if len(jobs) > 0:
                job = jobs[0]
                job.status = STATUS_RUNNING
                job.save()
                return job
        return None

    def add_arguments(self, parser):
        # https://docs.djangoproject.com/en/2.1/howto/custom-management-commands/
        # https://docs.python.org/3/library/argparse.html#module-argparse
        help = "If given a one or more job_id the worker will process those jobs then quit, otherwise it will retrieve pending jobs from the pending jobs queue"
        parser.add_argument("job_id", nargs="*", type=str, help=help)
        help = "Process this many jobs then quit (default: zero for unlimited jobs)"
        parser.add_argument("--max-jobs", default=0, type=int, help=help)
        help = "Work this many seconds then quit (default: zero for unlimited time)"
        parser.add_argument("--max-secs", default=0, type=int, help=help)
        help = "Tags used to filter jobs, eg: staging premium xxl"
        parser.add_argument("--tags", nargs="*", type=str, help=help)

    def handle(self, *args, **options):
        """ Called when command is run will keep processing jobs """
        self.info("worker: started, id: %s", self.id)

        # if given a list of jobs to perform, run them then quit
        if len(options["job_id"]) > 0:
            for job_id in options["job_id"]:
                try:
                    job = factory.get_item(job_id)
                    job.status = STATUS_RUNNING
                    job.save()
                    self.run_job(job)
                except:
                    return WORKER_ERROR
            self.info("worker: quitting, completed command line jobs, bye")
            return WORKER_SUCCESS

        max_jobs = options["max_jobs"]
        processed_jobs = 0
        max_secs = options["max_secs"]
        started_ms, idle_ms = time_ms(), time_ms()

        # loop on pending jobs until: max number of jobs, max time, quit signal
        while self.running:
            try:
                job = self.get_pending_job(**options)
                if job:
                    processed_jobs = processed_jobs + 1
                    self.run_job(job)
                    # no delay before next job
                else:
                    if int(time_ms(idle_ms) / 1000) > 120:
                        uptime_sec = int(time_ms(started_ms) / 1000)
                        self.info("worker: idle, uptime: %ds", uptime_sec)
                        idle_ms = time_ms()
                    time.sleep(POLLING_DELAY_SHORT)
            except:
                # sleep a little before returning to avoid getting
                # stuck in really quick loops of failure-relaunch, repeat-rinse
                time.sleep(POLLING_DELAY_LONG)
                return WORKER_ERROR

            if max_jobs > 0 and processed_jobs >= max_jobs:
                self.info("worker: quitting, max-jobs: %d completed, bye", processed_jobs)
                return WORKER_SUCCESS

            if max_secs > 0 and int(time_ms(started_ms) / 1000) >= max_secs:
                self.info("worker: quitting, max-secs: %ds expired, bye", max_secs)
                return WORKER_SUCCESS

        self.info("worker: quitting, stop requested, bye")
        return WORKER_SUCCESS
