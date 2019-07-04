import collections
import jsonfield
import django.utils.crypto
import logging
import logging.handlers
import queue
import datetime
import pytz

from django.db import models
from django.conf import settings
from rest_framework.request import Request

from .items import ItemMixin
from .workspace import Workspace
from .job import Job

import analitico
import analitico.plugin
import analitico.utilities
import api.utilities

LOG_LEVEL_NOTSET = 0
LOG_LEVEL_DEBUG = 10
LOG_LEVEL_INFO = 20
LOG_LEVEL_WARNING = 30
LOG_LEVEL_ERROR = 40
LOG_LEVEL_CRITICAL = 50


def generate_log_id():
    """ All Log.id have jb_ prefix followed by a random string """
    return analitico.LOG_PREFIX + django.utils.crypto.get_random_string(length=6)


##
## DEPRECATED DO NOT USE
##


class Log(ItemMixin, models.Model):
    """ A log entry used to track events on clients, workers and servers. """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_log_id)

    # Log entry can be owned by workspace or can be system wide if None
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, blank=True, null=True)

    # Log entry can be owned by a Job
    job = models.ForeignKey(Job, on_delete=models.CASCADE, blank=True, null=True)

    # Item that generated this log entry (optional)
    item_id = models.SlugField(blank=True, null=True, db_index=True)

    # https://docs.python.org/3.7/library/logging.html?highlight=logging#logging-levels
    level = models.IntegerField(default=LOG_LEVEL_NOTSET, db_index=True)

    # Log formatted message (using title so it's the same as all other models and also gets serialized outside attributes)
    title = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="created")

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    @property
    def name(self):
        return self.get_attribute("name", None)

    @property
    def level_name(self):
        return logging.getLevelName(self.level)

    def __str__(self):
        return self.id + " " + self.title
