from croniter import croniter
from datetime import datetime
from django.utils import timezone

from analitico import ACTION_PROCESS, ACTION_TRAIN
from analitico.utilities import get_dict_dot, set_dict_dot
from analitico.status import STATUS_CREATED
from api.models import Dataset, Recipe, Notebook, Job


# This library could be used to schedule jobs automatically:
# https://gitlab.com/doctormo/python-crontab/


def schedule_items(items, action):
    """ Takes a list of datasets, recipes or notebooks and creates jobs for any scheduled updates """
    jobs = []
    for item in items:
        schedule = item.get_attribute("schedule")
        if schedule and "cron" in schedule:
            # what is the cron configuration string used to schedule this item?
            # https://en.wikipedia.org/wiki/Cron
            cron = schedule.get("cron", None)

            # when was this item last scheduled?
            scheduled_at = schedule.get("scheduled_at", None)
            scheduled_at = item.updated_at

            schedule_next = croniter(cron, scheduled_at).get_next(datetime)
            now = timezone.now()
            if schedule_next < now:
                # create the job that will process the item
                job = Job(item_id=item.id, action=action, workspace_id=item.workspace_id, status=STATUS_CREATED)
                job.set_attribute("schedule", schedule)
                job.save()

                # update the schedule and keep track of job that last ran this item
                schedule["scheduled_at"] = now.isoformat()
                schedule["scheduled_job"] = job.id
                item.set_attribute("schedule", schedule)
                item.save()

                jobs.append(job)
    return jobs


def schedule_jobs():
    """ 
    Checks to see if any datasets, recipes or notebooks need to run 
    on a schedule and generates the necessary jobs. Returns an array
    of jobs (or None if no job was generated).
    """
    nb_jobs = schedule_items(Notebook.objects.all(), ACTION_PROCESS)
    ds_jobs = schedule_items(Dataset.objects.all(), ACTION_PROCESS)
    rx_jobs = schedule_items(Recipe.objects.all(), ACTION_PROCESS)
    return nb_jobs + ds_jobs + rx_jobs
