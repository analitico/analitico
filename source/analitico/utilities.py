import os
import time
import pandas as pd
import logging
import socket
import platform
import multiprocessing
import psutil
import collections
import subprocess
import sys
import random
import string
import dateutil
import re
import subprocess
import traceback

from collections import OrderedDict

# use simplejson instead of standard built in library
# mostly because it has a parameter which supports replacing nan with nulls
# thus producing json which is ecma compliant and won't have issues being read
# https://simplejson.readthedocs.io/en/latest/
import simplejson as json

from datetime import datetime

try:
    import distro
    import GPUtil
except Exception:
    pass

from analitico.exceptions import AnaliticoException
from analitico.schema import analitico_to_pandas_type, apply_schema, NA_VALUES

# default logger for analitico's libraries
logger = logging.getLogger("analitico")


# RESTful API Design Tips from Experience
# https://medium.com/studioarmix/learn-restful-api-design-ideals-c5ec915a430f

# Trying to follow this spec for naming, etc
# https://jsonapi.org/format/#document-top-level

# Following this format for errors:
# https://jsonapi.org/format/#errors


##
## Exceptions
##


def first_or_list(items):
    try:
        if items and len(items) == 1:
            return items[0]
    except Exception:
        pass  # validation errors pass a dictionary so we just pass it through
    return items


def exception_to_dict(exception: Exception, add_context=True, add_formatted=True, add_traceback=True) -> dict:
    """ Returns a dictionary with detailed information on the given exception and its inner (chained) exceptions """

    # trying to adhere as much as possible to json:api specs here
    # https://jsonapi.org/format/#errors
    d = OrderedDict()
    d["status"] = "500"  # want this to go first
    d["code"] = type(exception).__name__.lower()
    d["title"] = str(exception.args[0]) if len(exception.args) > 0 else str(exception)
    d["meta"] = {}

    if isinstance(exception, AnaliticoException):
        d["status"] = str(exception.status_code)
        d["code"] = exception.code
        d["title"] = exception.message
        if exception.extra and len(exception.extra) > 0:
            d["meta"]["extra"] = json_sanitize_dict(exception.extra)

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
    if len(d["meta"]) < 1:
        d.pop("meta")
    return d


##
## Crypto
##


def id_generator(size=9, chars=string.ascii_letters + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


##
## Runtime
##

MB = 1024 * 1024


def get_runtime_brief():
    """ A digest version of get_runtime to be used more frequently """
    return {"cpu_count": multiprocessing.cpu_count()}


def get_gpu_runtime():
    """ Returns array of GPU specs (if discoverable) """
    try:
        runtime = []
        # optional package
        GPUs = GPUtil.getGPUs()
        if GPUs:
            for GPU in GPUs:
                runtime.append(
                    {
                        "uuid": GPU.uuid,
                        "name": GPU.name,
                        "driver": GPU.driver,
                        "temperature": int(GPU.temperature),
                        "load": round(GPU.load, 2),
                        "memory": {
                            "total_mb": int(GPU.memoryTotal),
                            "available_ms": int(GPU.memoryFree),
                            "used_mb": int(GPU.memoryUsed),
                            "used_perc": round(GPU.memoryUtil, 2),
                        },
                    }
                )
    except Exception:
        return None
    return runtime


def get_runtime():
    """ Collect information on runtime environment, platform, python, hardware, etc """
    started_on = time_ms()
    runtime = collections.OrderedDict()
    try:
        runtime["hostname"] = socket.gethostname()
        runtime["ip"] = socket.gethostbyname(socket.gethostname())
        runtime["platform"] = {"system": platform.system(), "version": platform.version()}
        try:
            # optional package
            runtime["platform"]["name"] = distro.name()
            runtime["platform"]["version"] = distro.version()
        except Exception:
            pass

        runtime["python"] = {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "encoding": sys.getdefaultencoding(),
        }

        hardware = collections.OrderedDict()
        runtime["hardware"] = hardware
        hardware["cpu"] = {"type": platform.processor(), "count": multiprocessing.cpu_count()}
        try:
            # will raise exception on virtual machines
            hardware["cpu"]["freq"] = int(psutil.cpu_freq()[2])
        except:
            pass

        gpu = get_gpu_runtime()
        if gpu:
            hardware["gpu"] = gpu

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        hardware["memory"] = {
            "total_mb": int(memory.total / MB),
            "available_mb": int(memory.available / MB),
            "used_mb": int(memory.used / MB),
            "swap_mb": int(swap.total / MB),
            "swap_perc": round(swap.percent, 2),
        }

        disk = psutil.disk_usage("/")
        hardware["disk"] = {
            "total_mb": int(disk.total / MB),
            "available_mb": int(disk.free / MB),
            "used_mb": int(disk.used / MB),
            "used_perc": round(disk.percent, 2),
        }

        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = (datetime.now() - boot_time).total_seconds() / 3600
        runtime["uptime"] = {"since": boot_time.strftime("%Y-%m-%d %H:%M:%S"), "hours": round(uptime, 2)}

        # production servers have an environment variable indicating git commit
        runtime["github"] = {}
        try:
            v = subprocess.check_output(["git", "describe"]).decode("utf-8").strip()
            runtime["github"]["version"] = v
        except:
            pass
        commit_sha = os.environ.get("ANALITICO_COMMIT_SHA", None)
        if commit_sha:
            runtime["github"]["commit"] = commit_sha
            runtime["github"]["url"] = "https://github.com/analitico/analitico/commit/" + commit_sha
    except Exception as exc:
        runtime["exception"] = str(exc)

    runtime["elapsed_ms"] = time_ms(started_on)
    return runtime


##
## Json utilities
##

JSON_NOT_SERIALIZABLE = "NOT_SERIALIZABLE"


def json_sanitize_dict(dict):
    """ Remove from dictionary all items which cannot be easily serialized to json, replace with item_id where possible. """
    sanitized = json.loads(json.dumps(dict, skipkeys=True, default=lambda o: JSON_NOT_SERIALIZABLE))
    for key in dict:
        if sanitized[key] == JSON_NOT_SERIALIZABLE:
            try:
                # if an item could note be serialized, let's see if we can replace it with its id
                key_id = key + "_id"
                if key_id not in sanitized:
                    sanitized[key_id] = dict[key].id
                    sanitized.pop(key)
            except:
                # item doesn't have an .id
                pass
    return sanitized


def save_json(data, filename, indent=None, encoding="utf8", ignore_nan=True):
    """ Saves given data in a json file, encodes as utf-8, replace np.NaN with nulls """
    with open(filename, "w", encoding=encoding) as f:
        json.dump(data, f, indent=indent, ignore_nan=ignore_nan)


def read_json(filename, encoding="utf-8"):
    """ Reads, decodes and returns the contents of a json file """
    try:
        with open(filename, encoding=encoding) as f:
            return json.load(f)
    except Exception as exc:
        detail = "analitico.utilities.read_json: error while reading {}, exception: {}".format(filename, exc)
        logger.error(detail)
        raise Exception(detail, exc)


def read_text(filename, encoding="utf-8"):
    """ Reads a text file """
    try:
        with open(filename, encoding=encoding) as f:
            return f.read()
    except Exception as exc:
        detail = "analitico.utilities.read_text: error while reading {}, exception: {}".format(filename, exc)
        logger.error(detail)
        raise Exception(detail, exc)


def save_text(text, filename):
    with open(filename, "w") as text_file:
        text_file.write(text)


##
## Time utilities
##


def time_ms(started_on=None):
    """ Returns the time elapsed since given time in ms """
    return datetime.now() if started_on is None else int((datetime.now() - started_on).total_seconds() * 1000)


# https://docs.python.org/2/library/functools.html
# used as @timeit decorator
# https://medium.com/pythonhive/python-decorator-to-measure-the-execution-time-of-methods-fa04cb6bb36d
def timeit(method):
    def timed(*args, **kwargs):
        ts = time.time()
        result = method(*args, **kwargs)
        ms = int((time.time() - ts) * 1000)

        # if self has logger, log to it
        if hasattr(args[0], "logger"):
            try:
                args[0].logger.info("%s in %d ms", method.__name__.lower(), ms)
            except:
                pass
        else:
            print("%s in %d ms", method.__name__.lower(), ms)

        return result

    return timed


##
## Timestamp utilities
##


def timestamp_to_time(ts: str, ts_format="%Y-%m-%d %H:%M:%S") -> time.struct_time:
    """ Converts a timestamp string in the given format to a time object """
    try:
        return time.strptime(ts, ts_format)
    except TypeError:
        return None


def timestamp_to_secs(ts: str, ts_format="%Y-%m-%d %H:%M:%S") -> float:
    """ Converts a timestamp string to number of seconds since epoch """
    return time.mktime(time.strptime(ts, ts_format))


def timestamp_diff_secs(ts1, ts2):
    t1 = timestamp_to_secs(ts1)
    t2 = timestamp_to_secs(ts2)
    return t1 - t2


##
## Dictionary utilities
##


def get_dict_dot(d: dict, key: str, default=None):
    """ Gets an entry from a dictionary using dot notation key, eg: this.that.something """
    try:
        if isinstance(d, dict) and key:
            split = key.split(".")
            value = d.get(split[0])
            if value:
                if len(split) == 1:
                    return value
                return get_dict_dot(value, key[len(split[0]) + 1 :], default)
    except KeyError:
        pass
    return default


def set_dict_dot(d: dict, key: str, value=None):
    """ Sets an entry from a dictionary using dot notation key, eg: this.that.something """
    if isinstance(d, dict) and key:
        split = key.split(".")
        subkey = split[0]
        if len(split) == 1:
            d[subkey] = value
            return
        if not (subkey in d):
            d[subkey] = OrderedDict()
        set_dict_dot(d[subkey], key[len(subkey) + 1 :], value)


##
## CSV
##


def get_csv_row_count(filename):
    """ Returns the number of rows in the given csv file (one row is deducted for the header) """
    with open(filename, "r") as f:
        return sum(1 for row in f) - 1


##
## Regular expression
##


def re_match_group(expression: str, content: str, default: str = None, group_index: int = 1) -> str:
    """ Searches for the first matching group or returns the default value """
    match = re.search(expression, content)
    if match:
        return match.group(group_index)
    return default


##
## Text
##


def comma_separated_to_array(items: str) -> [str]:
    """ Turns a string with a comma separated list of items into an array of strings """
    if items and items.strip():
        return [x.strip() for x in items.split(",")]
    return None


def array_to_comma_separated(items: [str]) -> str:
    """ Turns an array of items into a comma separated string """
    if items and len(items) > 0:
        return ",".join(items)
    return None


##
## Subprocess
##


def json_from_string_if_possible(value: str):
    """ If your string is json then it will be parsed and returned otherwise you just get your string back """
    try:
        return json.loads(value) if len(value) > 4 else value
    except:
        pass
    return value


def subprocess_run(cmd_args, job=None, timeout=3600, cwd=None) -> (str, str):
    """
    Run a subprocess with the given command arguments. Logs the command, the response
    and the time it took to run it. If an error occours, raises an explanatory exception
    otherwise it returns the stdout and stderr from the command possibly parse as json
    if the response was in json.
    """
    message = "subprocess_run:\n" + " ".join(cmd_args)
    logger.info(message)
    if job:
        job.append_logs(message)

    started_on = time_ms()
    response = subprocess.run(
        cmd_args, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, cwd=cwd
    )

    elapsed_ms = time_ms(started_on)
    message = (
        f"completed in {elapsed_ms} ms, returned code: {response.returncode}\n\n{response.stdout}\n\n{response.stderr}"
    )
    logger.info(message)
    if job:
        job.append_logs(message)

    if response.returncode:
        message = "An error occoured while executing '" + " ".join(cmd_args) + "'."
        if response.stdout:
            message += "\nResponse.stdout:\n" + response.stdout
        if response.stderr:
            message += "\nResponse.stderr:\n" + response.stderr
        logger.error(message)
        raise AnaliticoException(message)

    stdout = json_from_string_if_possible(response.stdout)
    stderr = json_from_string_if_possible(response.stderr)
    return stdout, stderr
