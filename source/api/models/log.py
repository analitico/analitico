import collections
import jsonfield
import django.utils.crypto
import json
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
## Job
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

    # Log formatted message
    message = models.TextField(blank=True)

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
        return self.id + " " + self.message


##
## Utilities
##

# log record attributes that are always dropped
LOG_RECORD_DROP_ALWAYS = (
    "args",
    "asctime",
    "created",
    "levelname",
    "levelno",
    "message",
    "msecs",
    "msg",
    "relativeCreated",
    "item_id",
    "relativeCreated",
)

# log record attributes that are dropped only when level is INFO or less
LOG_RECORD_DROP_INFO = (
    "exc_info",
    "filename",
    "funcName",
    "lineno",
    "module",
    "pathname",
    "process",
    "processName",
    "stack_info",
    "thread",
    "threadName",
)


def log_record_to_log(log_record: logging.LogRecord) -> Log:
    """ Creates an api.models.Log from a logging.LogRecord """
    log = Log()

    log.level = log_record.levelno
    log.message = log_record.message
    log.created_at = datetime.datetime.fromtimestamp(log_record.created, pytz.UTC)

    # create dictionary of attributes, remove unwanted keys
    attributes = log_record.__dict__
    attributes = {k: v for k, v in attributes.items() if v is not None}

    # remove keys according to message level
    for key in LOG_RECORD_DROP_ALWAYS:
        attributes.pop(key, None)
    if log_record.levelno <= LOG_LEVEL_INFO:
        for key in LOG_RECORD_DROP_INFO:
            attributes.pop(key, None)

    log.workspace = attributes.pop("workspace", None)
    log.job = attributes.pop("job", None)
    if log.job and not log.workspace:
        log.workspace = log.job.workspace

    # extract authorization details, caller details from Request
    request = attributes.pop("request", None)
    if request and isinstance(request, Request):
        # TODO extract auth details, caller IP
        pass

    # convert items to xxx_id
    for item_type in ("dataset", "recipe", "model", "endpoint", "plugin", "workspace", "item"):
        item = attributes.pop(item_type, None)
        if item:
            try:
                if item.id:
                    attributes[item_type + "_id"] = item.id
                if hasattr(item, "workspace") and not log.workspace:
                    log.workspace = item.workspace
            except Exception as e:
                pass

    # move item_id to its own field
    log.item_id = attributes.pop("item_id", None)

    exception = attributes.pop("exception", None)
    if exception:
        # TODO convert to json dictionary with all included inner exceptions
        attributes["exception"] = str(exception)

    # TODO add user or user ip info like sentry

    log.attributes = attributes
    return log


##
## Log handlers
##


class LogHandler(logging.NullHandler):
    """ This handler takes log records and stores them on the server """

    def handle(self, record):
        try:
            log = log_record_to_log(record)
            log.save()
            print("log, saved: %s" % record.message)
        except Exception as e:
            try:
                # we use atttributes to save in json a number of items
                # that have been passed to the logger some of which may not
                # be serializable to json. if this happens, we'll just encode
                # basic types and move on
                attrs = json.loads(json.dumps(log.attributes, skipkeys=True, default=lambda o: "NOT_SERIALIZABLE"))
                log.attributes = attrs
                log.save()
                print("log encoded/saved: %s" % record.message)
            except Exception as e:
                # do not log errors here otherwise they will be captured by log handler, repeat, rinse, etc..
                print("log saving error: %s" % record.message)
                pass


# This handler simply takes a log record, sticks it in the queue and returns w/o blocking """
class LogQueueHandler(logging.handlers.QueueHandler):
    """ This handler runs LogHandler with a queue so it doesn't slow down client while logging """

    log_handler = None
    log_listener = None

    def __init__(self, log_queue=None, **kwargs):
        if log_queue is None:
            log_queue = queue.Queue(-1)  # no limit on size
        self.log_handler = LogHandler()
        self.log_listener = logging.handlers.QueueListener(log_queue, self.log_handler)
        self.log_listener.start()
        return super().__init__(log_queue, **kwargs)


##
## Setup
##

USE_LOG_QUEUE = False

log_handler = None

if log_handler is None:
    # create a log handler to sql database
    if settings.IS_TESTING:
        # no async queue while testing
        log_handler = LogHandler()
    else:
        # handle logs asynchronously
        log_handler = LogQueueHandler()

    log_handler = LogQueueHandler()
    log_handler.setLevel(logging.INFO)
    # add to root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(log_handler)

logger = logging.getLogger("analitico")
logger.info("status: running")
