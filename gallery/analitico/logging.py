import logging
import logging.config
import time
import json

from datetime import datetime

# Adapted from marselester/json-log-formatter:
# https://github.com/marselester/json-log-formatter

BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class FluentdFormatter(logging.Formatter):
    """
    A log formatter used to collect logs on a kubernets cluster in a way that
    can be easily collected by fluentd deamons and the dispatched to elastich
    search so it can be visualized in analitico's dashboard with reach metadata.

    Usage example::
        import logging
        import json_log_formatter
        json_handler = logging.FileHandler(filename='/var/log/my-log.json')
        json_handler.setFormatter(json_log_formatter.FluentdFormatter())
        logger = logging.getLogger('my_json')
        logger.addHandler(json_handler)
        logger.info('Sign up', extra={'referral_code': '52d6ce'})

    The log file will contain the following log record (inline)::
        {
            "level": "warning", 
            "ts": "2019-07-03T10:27:59.430590", 
            "logger": "root", 
            "caller": "<module>:33", 
            "msg": "Sign up",
            "referral_code": "52d6ce"
        }
    """

    json_lib = json

    def format(self, record):
        message = record.getMessage()
        extra = self.extra_from_record(record)
        json_record = self.json_record(message, extra, record)
        mutated_record = self.mutate_json_record(json_record)
        # Backwards compatibility: Functions that overwrite this but don't
        # return a new value will return None because they modified the
        # argument passed in.
        if mutated_record is None:
            mutated_record = json_record
        return self.to_json(mutated_record)

    def to_json(self, record):
        """ 
        Converts record dict to a JSON string. 
        Override this method to change the way dict is converted to JSON. 
        """
        return self.json_lib.dumps(record)

    def extra_from_record(self, record):
        """
        Returns `extra` dict you passed to logger.
        The `extra` keyword argument is used to populate the `__dict__` of the `LogRecord`.
        """
        return {
            attr_name: record.__dict__[attr_name] for attr_name in record.__dict__ if attr_name not in BUILTIN_ATTRS
        }

    def json_record(self, message, extra, record):
        """
        Prepares a JSON payload which will be logged.
        Override this method to change JSON log format.
        :param message: Log message, e.g., `logger.info(msg='Sign up')`.
        :param extra: Dictionary that was passed as `extra` param
            `logger.info('Sign up', extra={'referral_code': '52d6ce'})`.
        :param record: `LogRecord` we got from `JSONFormatter.format()`.
        :return: Dictionary which will be passed to JSON lib.
        """
        extra["level"] = record.levelname.lower()
        if "ts" not in extra:
            extra["ts"] = datetime.utcnow()
        extra["logger"] = record.name
        if record.funcName and record.lineno:
            extra["caller"] = record.funcName + ":" + str(record.lineno)
        extra["msg"] = message
        if record.exc_info:
            extra["exc_info"] = self.formatException(record.exc_info)
        return extra

    def mutate_json_record(self, json_record):
        """
        Override it to convert fields of `json_record` to needed types.
        Default implementation converts `datetime` to string in ISO8601 format.
        """
        for attr_name in json_record:
            attr = json_record[attr_name]
            if isinstance(attr, datetime):
                json_record[attr_name] = attr.isoformat()
        return json_record
