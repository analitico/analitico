import collections
import jsonfield
import django.utils.crypto
import logging
import dateutil.parser

from croniter import croniter
from datetime import datetime, timedelta
from django.db import models
from django.utils import timezone

from .items import ItemMixin
from .workspace import Workspace

import analitico
import analitico.plugin
import analitico.utilities

from analitico import AnaliticoException, ACTION_PROCESS, ACTION_TRAIN, logger
from analitico.constants import ACTION_PREDICT, ACTION_RUN, ACTION_BUILD, ACTION_RUN_AND_BUILD
from analitico.status import (
    STATUS_CREATED,
    STATUS_RUNNING,
    STATUS_FAILED,
    STATUS_COMPLETED,
    STATUS_CANCELED,
    STATUS_ALL,
)
from api.factory import ServerFactory

# https://crontab.guru/examples.html
CRON_EVERY_MINUTE = "* * * * *"
CRON_EVERY_HOUR = "0 * * * *"


def generate_job_id():
    """ All Job.id have jb_ prefix followed by a random string """
    return analitico.JOB_PREFIX + analitico.utilities.id_generator()


##
## Job
##


class Job(ItemMixin, models.Model):
    """ 
    A job is a model for a piece of work like running an ETL pipeline, training a model,
    doiing a machine learning inference, etc. A job can run synchronously inside a web server
    if it is short (eg inference) or it can be run asynchronously by a worker etc.
    A job is normally completed by running the plugin owned by the requestor of the job.
    """

    ##
    ## Standard fields just like in all other Item models
    ##

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_job_id)

    # Model is always owned by one and only one workspace
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Description (markdown supported)
    description = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="created")

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True, verbose_name="updated")

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    ##
    ## Custom fields specific to job
    ##

    # Current status, eg: created, processing, completed, failed (see analitico.status for values)
    status = models.SlugField(blank=True, default="created")

    # The type of job, or action, for example: workspace/process, model/train, endpoint/inference, etc
    action = models.CharField(blank=True, max_length=64)

    # The item that is the target of this job (eg. model that is trained, dataset that is processed, etc)
    item_id = models.SlugField(blank=True)

    ##
    ## Properties
    ##

    @property
    def payload(self):
        """ Payload attached to the job (eg: an inference, job results, etc) """
        return self.get_attribute("payload", None)

    @payload.setter
    def payload(self, payload):
        self.set_attribute("payload", payload)

    def set_status(self, status: str, save: bool = True):
        """ Changes a job status and tracks changes in the log """
        if status != self.status:
            assert status in STATUS_ALL, f"job.set_status({status}) is not a valid status"
            logger.info(f"Job: {self.id} changing status from: {self.status}, to: {status}")
            self.status = status
            if save:
                self.save()

    ##
    ## Logging
    ##

    @property
    def logs(self):
        """ Logs attached produced while executing this job """
        return self.get_attribute("logs", "")

    @logs.setter
    def logs(self, logs):
        self.set_attribute("logs", logs)

    def append_logs(self, logs, save: bool = True):
        """ Appends given log string to this job's logs """
        if logs:
            self.logs = self.logs + logs + "\n"
            if save:
                self.save()

    ##
    ## Execution
    ##

    def run(self, request, **kwargs):
        """ Runs the job, collects and uploads artifacts, returns the updated job """
        with ServerFactory(job=self, request=request, **kwargs) as factory:
            try:
                # log only warnings while predicting to avoid slowing down predictions
                action = str(self.action)
                predicting = ACTION_PREDICT in action
                if predicting:
                    factory.set_logger_level(logging.WARNING)

                self.set_status(STATUS_RUNNING)

                # item runs the job
                item = factory.get_item(self.item_id)
                item.set_attribute("job_id", self.id)

                # apply an id to any plugin that may be missing one
                # and save the recipe with the new plugin ids so that
                # the job can track logged actions by each plugin
                plugin = item.get_attribute("plugin")
                if analitico.plugin.apply_plugin_id(plugin):
                    item.set_attribute("plugin", plugin)

                item.save()
                item.run(job=self, factory=factory)
                item.save()

                self.set_status(STATUS_COMPLETED)

            except AnaliticoException as exc:
                self.set_status(STATUS_FAILED)
                raise exc

            except Exception as exc:
                self.set_status(STATUS_FAILED)
                message = f"An error occoured while running job: {self.id} on item: {self.item_id}"
                raise analitico.AnaliticoException(message, item=self, job=self) from exc


##
## Utilities
##

JOB_TIMEOUT_MINUTES = 30

# DEPRECATED
# #329 jobs / kill the job run when takes if not complete in 6 hours
def timeout_jobs() -> [Job]:
    """ Find jobs that have been running for over 30 minutes (stuck) and mark them as failed """
    now = datetime.utcnow()
    earlier = now - timedelta(minutes=JOB_TIMEOUT_MINUTES)

    # pylint: disable=no-member
    jobs = list(Job.objects.filter(updated_at__lt=earlier, status=STATUS_RUNNING))
    for job in jobs:
        job.status = STATUS_CANCELED
        job.save()
    return jobs


# Some notebooks, datasets and recipes are set up with a "schedule"
# attribute which is used to specify when the item should be processed
# automatically with a syntax like that of cron. The server does not
# run cron jobs, rather it offers an endpoint on /api/jobs/schedule which
# is called to check if any item needs scheduling and create the job
# which is then processed asynchronously by the workers. This API is called
# every minute by our external monitoring platform hence making this automatic.

# This library could also be used to schedule jobs using cron on the server,
# the issue would then become that we have multiple servers and we would need to
# pick one of the servers to run this, etc...
# https://gitlab.com/doctormo/python-crontab/


def schedule_items(items, action: str) -> [dict]:
    """ Takes a list of datasets, recipes or notebooks and creates jobs for any scheduled updates """
    jobs = []
    for item in items:
        schedule = item.get_attribute("schedule")
        if schedule and "cron" in schedule:
            try:
                # what is the cron configuration string used to schedule this item?
                # https://en.wikipedia.org/wiki/Cron
                cron = schedule.get("cron")
                # the notebook to run
                notebook = schedule.get("notebook")

                # when was this item last scheduled?
                scheduled_at = schedule.get("scheduled_at", "2010-01-01T00:00:00Z")  # UTC
                scheduled_at = dateutil.parser.parse(scheduled_at)

                # when is this item next due according to its cron settings and the last time it was scheduled?
                schedule_next = croniter(cron, scheduled_at).get_next(datetime)
                now = timezone.now()

                label = "scheduling" if schedule_next < now else "skip"
                msg = f"schedule_items: {label}: {item.id}, cron: {cron}, scheduled_at: '{scheduled_at}, schedule_next: {schedule_next}"

                if schedule_next <= now:
                    analitico.logger.info(msg)
                    # create the job that will process the item
                    from api.k8 import k8_jobs_create
                    job_data = {"notebook": notebook} if notebook else None
                    job = k8_jobs_create(item, action, job_data=job_data)
                    jobs.append(job)

                    # update the schedule and keep track of job that last ran this item
                    schedule["scheduled_at"] = now.isoformat()
                    schedule["scheduled_job"] = job["metadata"]["name"]
                    item.set_attribute("schedule", schedule)
                    item.save()
                else:
                    analitico.logger.debug(msg)

            except Exception as exc:
                raise AnaliticoException(
                    f"schedule_items: an error occoured while trying to schedule '{item.id}' using cron '{cron}'"
                ) from exc
    return jobs


def schedule_jobs() -> [dict]:
    """ 
    Checks to see if any datasets, recipes or notebooks need to run 
    on a schedule and generates the necessary jobs. Returns an array
    of jobs that were scheduled (or None if no job was generated).
    Also scan 
    """
    # filter only items that contain "schedule" in their attributes
    # and may possibly be configured for automatic cron scheduling
    # pylint: disable=no-member
    from api.models import Dataset, Recipe, Notebook

    ds = Dataset.objects.filter(attributes__icontains='"schedule"')
    ds_jobs = schedule_items(ds, ACTION_RUN)

    rx = Recipe.objects.filter(attributes__icontains='"schedule"')
    rx_jobs = schedule_items(rx, ACTION_RUN)

    nb = Notebook.objects.filter(attributes__icontains='"schedule"')
    nb_jobs = schedule_items(nb, ACTION_RUN)

    # also cancel stuck jobs
    return nb_jobs + ds_jobs + rx_jobs
