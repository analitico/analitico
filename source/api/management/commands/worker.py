import os
import time

from analitico.status import STATUS_CREATED, STATUS_RUNNING

from api.models import Job
from analitico.utilities import logger, time_ms
from api.factory import ServerFactory, factory

from django.core.management.base import BaseCommand, CommandError

# Writing custom django-admin commands
# https://docs.djangoproject.com/en/2.1/howto/custom-management-commands/
# pylint: disable=no-member

WORKER_SUCCESS = 0  # generic success result
WORKER_ERROR = 100  # generic error code

POLLING_DELAY_SHORT = 0.500  # delay between succesfull queue polls
POLLING_DELAY_LONG = 5.0  # delay in case of errors


class Command(BaseCommand):
    """ A django command used to run training jobs, either any pending ones or those specifically indicated """

    help = "A worker for asynchrous jobs like pipeline processing, model training, etc."

    # TODO implement external quit signal?
    running = True

    def run_job(self, job) -> Job:
        """ Run job with given id """
        try:
            job.status = STATUS_RUNNING
            job.save()

            logger.info("job: %s, status: %s, action: %s", job.id, job.status, job.action)
            started_ms = time_ms()
            job.run(request=None, action=job.action)
            logger.info("job: %s, status: %s, action: %s, elapsed: %d ms", job.id, job.status, job.action, time_ms(started_ms))
            return job
        except Exception as e:
            logger.warning("job: %s, status: %s, action: %s", job.id, job.status, job.action, exc_info=e)
            raise e

    def get_pending_job(self, **options):
        # TODO use tags to further filter jobs
        # TODO order by time posted desc
        jobs = Job.objects.filter(status=STATUS_CREATED)
        # TODO implement status switch to processing with atomic transactional guarantee
        return jobs[0] if len(jobs) > 0 else None

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
        logger.info("Worker started")

        # if given a list of jobs to perform, run them then quit
        if len(options["job_id"]) > 0:
            for job_id in options["job_id"]:
                try:
                    job = factory.get_item(job_id)
                    self.run_job(job)
                except:
                    return WORKER_ERROR
            logger.info("Completed command line jobs, bye")
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
                    if time_ms(idle_ms) > 15 * 1000:
                        logger.info("Uptime: %ds, no pending jobs", int(time_ms(started_ms) / 1000))
                        idle_ms = time_ms()
                    time.sleep(POLLING_DELAY_SHORT)
            except:
                # sleep a little before returning to avoid getting
                # stuck in really quick loops of failure-relaunch, repeat-rinse
                time.sleep(POLLING_DELAY_LONG)
                return WORKER_ERROR

            if max_jobs > 0 and processed_jobs >= max_jobs:
                logger.info("Max-jobs: %d completed, bye", processed_jobs)
                return WORKER_SUCCESS

            if max_secs > 0 and int(time_ms(started_ms) / 1000) >= max_secs:
                logger.info("Max-secs: %ds expired, bye", max_secs)
                return WORKER_SUCCESS

        logger.info("Stop requested, bye")
        return WORKER_SUCCESS
