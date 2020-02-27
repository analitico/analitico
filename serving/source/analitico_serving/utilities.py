import sys
import traceback
from collections import OrderedDict
from analitico_serving.exceptions import AnaliticoException
import simplejson as json

def exception_to_dict(exception: Exception, add_context=True, add_formatted=True, add_traceback=True) -> dict:
    """ Returns a dictionary with detailed information on the given exception and its inner (chained) exceptions """

    # trying to adhere as much as possible to json:api specs here
    # https://jsonapi.org/format/#errors
    d = OrderedDict()
    d["status"] = "500"  # want this to go first
    d["code"] = type(exception).__name__.lower()
    d["title"] = str(exception.args[0]) if exception.args else str(exception)
    d["meta"] = {}

    if isinstance(exception, AnaliticoException):
        d["status"] = str(exception.status_code)
        d["code"] = exception.code
        d["title"] = exception.message
        if exception.extra and exception.extra:
            d["meta"]["extra"] = json.dumps(exception.extra)

    if add_context and exception.__context__:
        d["meta"]["context"] = exception_to_dict(
            exception.__context__, add_context=True, add_formatted=False, add_traceback=False
        )

    # information on exception currently being handled
    _, _, exc_traceback = sys.exc_info()

    if add_formatted:
        # printout of error condition
        d["meta"]["formatted"] = traceback.format_exception(type(exception), exception, exc_traceback)

    if add_traceback:
        # extract frame summaries from traceback and convert them
        # to list of dictionaries with file and line number information
        d["meta"]["traceback"] = []
        for fs in traceback.extract_tb(exc_traceback, 20):
            d["meta"]["traceback"].append(
                OrderedDict(
                    {
                        "summary": "File '{}', line {}, in {}".format(fs.filename, fs.lineno, fs.name),
                        "filename": fs.filename,
                        "line": fs.line,
                        "lineno": fs.lineno,
                        "name": fs.name,
                    }
                )
            )

    if d["status"] is None:
        d.pop("status")
    if not d["meta"]:
        d.pop("meta")
    return d