
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

from google.cloud import storage
from pathlib import Path

from analitico.api import ApiException

# internals for operations on google cloud storage
# https://googleapis.github.io/google-cloud-python/latest/storage/blobs.html
# https://gcloud-python.readthedocs.io/en/latest/storage/blobs.html

_BUCKET="analitico-api"

# cloud storage key is copied in user root (not under source control)
KEY_PATH = '~/analitico-api-key.json'

def _gcs_get_client():
    try: 
        return storage.Client()
    except:
        key_path = os.path.expanduser(KEY_PATH)
        return storage.Client.from_service_account_json(key_path)

def _get_bucket(bucket_id):
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

def storage_download_prj_settings(project_id):
    try:
        with open('../projects/' + project_id + '/settings.json') as jf:
            return json.load(jf)
    except:
        # catch and load from network
        return _gcs_download_json(_BUCKET, 'projects/' + project_id  +'/settings.json')

def storage_download_prj_model(project_id) -> Path:
    # TODO: check if file exists and is fresh and skip downloading again
    path = os.path.join(tempfile.gettempdir(), project_id + '.cbm')
    _gcs_download_to_filename(_BUCKET, 'projects/' + project_id  +'/model.cbm', path)
    return path

def storage_download_prj_file(project_id, blobname, filename):
    return _gcs_download_to_filename(_BUCKET, project_id + '/' + blobname, filename)

def storage_upload_prj_file(project_id, blobname, filename):
    blob = _create_blob(_BUCKET, 'projects/' + project_id + '/' + blobname)
    with open(filename, "rb") as tmpfile:
        blob.upload_from_file(tmpfile)
    return blob.public_url

def storage_open(path, prefer_cloud=False):
    """ Will open the file for reading at the given path, if that fails, will try same from google storage bucket """
    if prefer_cloud is False and os.path.isfile(path):
        print("storage_open('%s') - local file" % path)
        return open(path, 'r')
    blob = _get_blob(_BUCKET, path)
    url = blob.generate_signed_url(expiration=datetime.timedelta(hours=1), method='GET')
    response = requests.get(url, stream=True)
    print("storage_open('%s') - cloud storage" % path)
    return io.BytesIO(response.content)

def storage_path(path, prefer_cloud=False):
    """ Will open the file for reading at the given path, if that fails, will try same from google storage bucket """
    if prefer_cloud is False and os.path.isfile(path):
        print("storage_path('%s') - local file" % path)
        return path
    blob = _get_blob(_BUCKET, path)
    print("storage_path('%s') - cloud storage" % path)
    return blob.generate_signed_url(expiration=datetime.timedelta(hours=1), method='GET')

def storage_temp(path) -> str:
    """ Will download a storage file to a temp file and return its path """
    suffix = os.path.splitext(path)[1]
    temp_path = tempfile.mktemp(suffix=suffix, prefix='tmp')
    _gcs_download_to_filename(_BUCKET, path, temp_path)
    print("storage_temp('%s') - to %s" % (path, temp_path))
    return temp_path


def storage_cache(storage_path, file_path=None, ttl_sec=600) -> str:
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
    
    blob = _get_blob(_BUCKET, storage_path)
    if blob is None:
        raise ApiException("Could not find '%s' in storage" % storage_path, 404)

    # check if cached file is old but still valid (same md5 as cloud copy)
    if os.path.isfile(file_path):
        file_md5 = hashlib.md5(open(file_path,'rb').read()).digest()
        file_md5 = base64.standard_b64encode(file_md5).decode('utf-8')
        if file_md5 == blob.md5_hash:
            os.utime(file_path, (now, now))
            print("storage_cache('%s') - from cache (after md5 check)" % file_path)
            return file_path

    # download and refresh cache
    blob.download_to_filename(file_path + '.downloading')
    os.replace(file_path + '.downloading', file_path)
    os.utime(file_path, (now, now))
 
    print("storage_cache('%s') - from cloud storage" % file_path)
    return file_path
