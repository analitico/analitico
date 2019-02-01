import logging
import io
import os, os.path
import json
import tempfile
import datetime
import requests
import time
import hashlib
import base64
import pandas as pd

from analitico.utilities import logger
from rest_framework.exceptions import APIException, NotFound
from google.cloud import storage
from pathlib import Path

import google.cloud.storage
import google.cloud.storage.blob

# internals for operations on google cloud storage
# https://googleapis.github.io/google-cloud-python/latest/storage/blobs.html
# https://gcloud-python.readthedocs.io/en/latest/storage/blobs.html

# all files in storage start with this url
STORAGE_URL_PREFIX = "https://storage.googleapis.com/data.analitico.ai/"

# default storage bucket for analitico files
BUCKET = "data.analitico.ai"

# default time to live for cached files
CACHE_TTL_SEC = 600

# cloud storage key is copied in user root (not under source control)
KEY_PATH = "~/credentials/google-cloud-analitico-api-key.json"


def _gcs_get_client():
    try:
        return storage.Client()
    except:
        key_path = os.path.expanduser(KEY_PATH)
        try:
            return storage.Client.from_service_account_json(key_path)
        except:
            raise APIException("Cloud credentials missing")


def _get_bucket(bucket_id=BUCKET):
    client = _gcs_get_client()
    return client.get_bucket(bucket_id)


def _get_blob(bucket_id, blobname):
    return _get_bucket(bucket_id).get_blob(blobname)


def _create_blob(bucket_id, blobname):
    return storage.Blob(blobname, _get_bucket(bucket_id))


def _gcs_download_to_filename(bucket_id, blobname, filename):
    blob = _get_blob(bucket_id, blobname)
    blob.download_to_filename(filename)
    return filename


def _gcs_download_string(bucket_id, blobname):
    blob = _get_blob(bucket_id, blobname)
    return blob.download_as_string()


def _gcs_download_json(bucket_id, blobname):
    return json.loads(_gcs_download_string(bucket_id, blobname))


##
## PUBLIC
##


def storage_open(path, prefer_cloud=False):
    """ Will open the file for reading at the given path, if that fails, will try same from google storage bucket """
    if prefer_cloud is False and os.path.isfile(path):
        print("storage_open('%s') - local file" % path)
        return open(path, "r")
    blob = _get_blob(BUCKET, path)
    try:
        url = blob.generate_signed_url(expiration=datetime.timedelta(hours=1), method="GET")
        response = requests.get(url, stream=True)
        print("storage_open('%s') - cloud storage" % path)
        return io.BytesIO(response.content)
    except Exception as exception:
        detail = str(exception) if exception.args[0] is None else exception.args[0]
        print("storage_open(%s) - exception: %s" % (path, detail))
        raise APIException("storage_open", 500)


def storage_path(path, prefer_cloud=False):
    """ Will open the file for reading at the given path, if that fails, will try same from google storage bucket """
    try:
        if prefer_cloud is False and os.path.isfile(path):
            print("storage_path('%s') - local file" % path)
            return path
        blob = _get_blob(BUCKET, path)
        print("storage_path('%s') - cloud storage" % path)
        return blob.generate_signed_url(expiration=datetime.timedelta(hours=1), method="GET")
    except Exception as exception:
        detail = str(exception) if exception.args[0] is None else exception.args[0]
        print("storage_path(%s) - exception: %s" % (path, detail))
        raise APIException("storage_open", 500)


def storage_temp(path) -> str:
    """ Will download a storage file to a temp file and return its path """
    suffix = os.path.splitext(path)[1]
    temp_path = tempfile.mktemp(suffix=suffix, prefix="tmp")
    _gcs_download_to_filename(BUCKET, path, temp_path)
    print("storage_temp('%s') - to %s" % (path, temp_path))
    return temp_path


def storage_cache(storage_path, file_path=None, ttl_sec=CACHE_TTL_SEC) -> str:
    """ Will download a storage file to a local cache (if needed) and return its path """
    if file_path is None:
        file_path = storage_path

    now = time.time()

    # check if file is more recent than requested in ttl_sec
    if os.path.isfile(file_path):
        touched_sec = int(now - os.path.getctime(file_path))
        if touched_sec < ttl_sec:
            print("storage_cache('%s') - from cache (modified %ds ago)" % (file_path, touched_sec))
            return file_path

    blob = _get_blob(BUCKET, storage_path)
    if blob is None:
        raise APIException("Could not find '%s' in storage" % storage_path, 404)

    # check if cached file is old but still valid (same md5 as cloud copy)
    if os.path.isfile(file_path):
        file_md5 = hashlib.md5(open(file_path, "rb").read()).digest()
        file_md5 = base64.standard_b64encode(file_md5).decode("utf-8")
        if file_md5 == blob.md5_hash:
            os.utime(file_path, (now, now))
            print("storage_cache('%s') - from cache (after md5 check)" % file_path)
            return file_path

    # download and refresh cache
    blob.download_to_filename(file_path + ".downloading")
    os.replace(file_path + ".downloading", file_path)
    os.utime(file_path, (now, now))

    print("storage_cache('%s') - from cloud storage" % file_path)
    return file_path


##
## v2
##


def upload_authorization(blobname):
    """ Obtains a signed url that can be used to upload a file to the given pathname """
    bucket = _get_bucket()
    blob = google.cloud.storage.blob.Blob(blobname, bucket)
    upload_url = blob.create_resumable_upload_session()
    return {"url": STORAGE_URL_PREFIX + blobname, "upload_url": upload_url}


def upload_file(blobname, filename):
    """ Uploads contents of file to a blob in storage and returns its url """
    blob = _create_blob(BUCKET, blobname)
    with open(filename, "rb") as tmpfile:
        blob.upload_from_file(tmpfile)
    return blob.public_url


def download_file(url, filename=None, cache_ttl=CACHE_TTL_SEC) -> str:
    """ Downloads a file in storage from given url to given filename, if cached returns local copy """

    # if url is a local file, just return that
    if os.path.isfile(url):
        return url

    if not url.startswith(STORAGE_URL_PREFIX):
        raise NotFound(url + " is not a storage url")

    blobname = url[len(STORAGE_URL_PREFIX) :]
    if filename is None:
        temp_dir = tempfile.gettempdir()
        filename = os.path.join(temp_dir, blobname)

    now = time.time()

    # check if file is more recent than requested in ttl_sec
    if os.path.isfile(filename):
        touched_sec = int(now - os.path.getctime(filename))
        if touched_sec < cache_ttl:
            logger.info("download_file: %s (from cache, modified %ds ago)", filename, touched_sec)
            return filename

    # TODO download and cache URL which are not in our storage

    blob = _get_blob(BUCKET, blobname)
    if blob is None:
        raise NotFound(blobname + " was not found in storage")

    # check if cached file is old but still valid (same md5 as cloud copy)
    if os.path.isfile(filename):
        file_md5 = hashlib.md5(open(filename, "rb").read()).digest()
        file_md5 = base64.standard_b64encode(file_md5).decode("utf-8")
        if file_md5 == blob.md5_hash:
            os.utime(filename, (now, now))
            logger.info("download_file: %s (from cache after md5 check)" % filename)
            return filename

    # download and refresh cache
    filedir = os.path.dirname(filename)
    if not os.path.isdir(filedir):
        os.makedirs(filedir)
    blob.download_to_filename(filename + ".downloading")
    os.replace(filename + ".downloading", filename)
    os.utime(filename, (now, now))

    logger.info("download_file: %s (from cloud storage)" % filename)
    return filename
