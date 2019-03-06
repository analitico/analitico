import collections
import jsonfield
import django.utils.crypto
import json
import logging
import queue
import datetime
import pytz

from django.db import models

from .items import ItemMixin
from .workspace import Workspace

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

    # Item that generated this log entry (optional)
    item_id = models.SlugField(blank=True, db_index=True)

    # https://docs.python.org/3.7/library/logging.html?highlight=logging#logging-levels
    level = models.IntegerField(default=LOG_LEVEL_NOTSET, db_index=True)

    # Log formatted message
    message = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="created")

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

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

    if "item_id" in attributes:
        log.item_id = attributes["item_id"]

    # TODO add workspace from workspace_id
    # TODO add user or user ip info like sentry

    # remove keys according to message level
    for key in LOG_RECORD_DROP_ALWAYS:
        attributes.pop(key, None)
    if log_record.levelno <= LOG_LEVEL_INFO:
        for key in LOG_RECORD_DROP_INFO:
            attributes.pop(key, None)
    log.attributes = attributes
    return log


##
## Log handlers
##


class LogQueueHandler(logging.handlers.QueueHandler):
    """ This handler simply takes a log record, sticks it in the queue and returns w/o blocking """

    pass


class LogQueueListener(logging.handlers.QueueListener):
    pass


class LogHandler(logging.NullHandler):
    """ This handler takes log records and stores them on the server """

    def handle(self, record):
        try:
            print("LogHandler - handle %s" % record.message)
            log = log_record_to_log(record)
            log.save()
        except Exception:
            try:
                # we use atttributes to save in json a number of items
                # that have been passed to the logger some of which may not
                # be serializable to json. if this happens, we'll just encode
                # basic types and move on
                log.attributes = json.loads(json.dumps(log.attributes, skipkeys=True))
                log.save()
            except Exception:
                # do not log errors here otherwise they will be captured by log handler, repeat, rinse, etc..
                pass


try:
    # setup a log queue handler that enqueues records quickly w/o blocking
    log_queue = queue.Queue(-1)  # no limit on size
    log_queue_handler = LogQueueHandler(log_queue)
    log_queue_handler.setLevel(logging.INFO)

    # handler will be called in a separate thread
    log_handler = LogHandler()

    log_listener = LogQueueListener(log_queue, log_handler)
    log_listener.start()

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(log_queue_handler)
except Exception as exc:
    print("ERROR " + str(exc))
