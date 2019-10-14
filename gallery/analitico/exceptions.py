import sys

from analitico import logger


class AnaliticoException(Exception):
    """ Base exception used in the project that can carry extra information with it in the form of a dictionary """

    default_message = "An error occurred."
    default_code = "error"
    default_status_code = 500

    message = None
    code = None
    status_code = None
    extra = None

    def __init__(self, message, *args, code=None, status_code=None, extra=None, **kwargs):
        try:
            self.message = message % (args)
        except:
            self.message = message if message else self.default_message

        self.code = code if code else self.default_code

        # we should pass the http status code by using status_code
        # however there are other classes that use status so this is
        # easy to confuse. use whatever parameter was passed.
        if status_code:
            self.status_code = status_code
        elif kwargs.get("status"):
            self.status_code = kwargs["status"]
        else:
            self.status_code = self.default_status_code

        self.extra = extra if extra else {}
        for key, value in kwargs.items():
            self.extra[key] = value

        logger.error(self)

    def __str__(self):
        return f"AnaliticoException - message: {self.message}, status_code: {self.status_code}"
