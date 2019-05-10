from croniter import croniter
from datetime import datetime, timedelta
import dateutil.parser
from django.utils import timezone

import analitico
from analitico import AnaliticoException, ACTION_PROCESS, ACTION_TRAIN
from analitico.status import STATUS_RUNNING, STATUS_CANCELED
from api.models import Dataset, Recipe, Notebook, Job

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


def schedule_items(items, action):
    """ Takes a list of datasets, recipes or notebooks and creates jobs for any scheduled updates """
    jobs = []
    for item in items:
        schedule = item.get_attribute("schedule")
        if schedule and "cron" in schedule:
            try:
                # what is the cron configuration string used to schedule this item?
                # https://en.wikipedia.org/wiki/Cron
                cron = schedule.get("cron")

                # when was this item last scheduled?
                scheduled_at = schedule.get("scheduled_at", "2010-01-01T00:00:00Z")  # UTC
                scheduled_at = dateutil.parser.parse(scheduled_at)

                # when is this item next due according to its cron settings and the last time it was scheduled?
                schedule_next = croniter(cron, scheduled_at).get_next(datetime)
                now = timezone.now()

                label = "scheduling" if schedule_next < now else "skip"
                msg = f"schedule_items: {label}: {item.id}, cron: {cron}, scheduled_at: '{scheduled_at}, schedule_next: {schedule_next}"

                if schedule_next < now:
                    analitico.logger.info(msg)
                    # create the job that will process the item
                    job = item.create_job(action)
                    job.set_attribute("schedule", schedule)
                    job.save()
                    jobs.append(job)

                    # update the schedule and keep track of job that last ran this item
                    schedule["scheduled_at"] = now.isoformat()
                    schedule["scheduled_job"] = job.id
                    item.set_attribute("schedule", schedule)
                    item.save()
                else:
                    analitico.logger.debug(msg)

            except Exception as exc:
                raise AnaliticoException(
                    f"schedule_items: an error occoured while trying to schedule '{item.id}' using cron '{cron}'"
                ) from exc
    return jobs


def schedule_jobs():
    """ 
    Checks to see if any datasets, recipes or notebooks need to run 
    on a schedule and generates the necessary jobs. Returns an array
    of jobs that were scheduled (or None if no job was generated).
    """
    # filter only items that contain "schedule" in their attributes
    # and may possibly be configured for automatic cron scheduling
    # pylint: disable=no-member

    ds = Dataset.objects.filter(attributes__icontains='"schedule"')
    ds_jobs = schedule_items(ds, ACTION_PROCESS)

    rx = Recipe.objects.filter(attributes__icontains='"schedule"')
    rx_jobs = schedule_items(rx, ACTION_TRAIN)

    nb = Notebook.objects.filter(attributes__icontains='"schedule"')
    nb_jobs = schedule_items(nb, ACTION_PROCESS)

    return nb_jobs + ds_jobs + rx_jobs

