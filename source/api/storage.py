import django.conf

from rest_framework.exceptions import NotFound
from pprint import pprint

import libcloud
import libcloud.storage.base
import libcloud.storage.types
import libcloud.storage.drivers.google_storage

# Storage options are configured from json blobs looking like this:
# {
#   "driver": "google-storage",
#   "container": "container.domain.ext",
#   "basepath": "",
#   "credentials": {
#     "key": "account-name@appspot.gserviceaccount.com",
#     "secret": "-----BEGIN PRIVATE KEY-----\nfAk...eKy=\n-----END PRIVATE KEY-----",
#     "project": "account-name"
#   }
# }

# Apache Libcloud
# https://libcloud.apache.org

# Storage base APIs
# https://libcloud.readthedocs.io/en/latest/storage/api.html

# Google Storage driver
# https://libcloud.readthedocs.io/en/latest/storage/drivers/google_storage.html


class StorageError(Exception):
    """ Exception used for storage issues """

    pass


class Storage:
    """ A cloud storage class that is provider independent """

    # settings used to initialize storage
    settings: dict = None

    # libcloud driver used to access storage
    driver: libcloud.storage.base.StorageDriver = None

    # default container
    container: libcloud.storage.base.Container = None

    def __init__(self, settings, driver):
        self.settings = settings
        self.driver = driver
        try:
            self.container = driver.get_container(settings["container"])
        except libcloud.storage.types.ContainerDoesNotExistError:
            self.container = driver.create_container(settings["container"])

    @staticmethod
    def factory(settings: dict):
        """ Creates a storage object from a settings dictionary or from default settings if None passed. """
        try:
            if settings is None:
                settings = django.conf.settings.ANALITICO_STORAGE
            if "credentials" not in settings and settings["driver"] == django.conf.settings.ANALITICO_STORAGE["driver"]:
                settings["credentials"] = django.conf.settings.ANALITICO_STORAGE["credentials"]

            driver = settings["driver"]
            credentials = settings["credentials"]
            assert driver
            assert credentials

            if driver == "google-storage":
                try:
                    # add newline in case it's lost from the environment variable...
                    settings["credentials"]["secret"] = settings["credentials"]["secret"].replace("{newline}", "\n")
                    driver = libcloud.storage.drivers.google_storage.GoogleStorageDriver(**credentials)
                    return Storage(settings, driver)
                except ValueError as exc:
                    raise Exception(
                        "Storage.factory - could not login to Google Cloud Storage, please check environment variables ANALITICO_GCS_KEY and ANALITICO_GCS_SECRET to make sure they are valid",
                        exc,
                    )

            # TODO add other cloud providers as we need them
            raise NotFound("Storage.factory - driver for '" + driver + "' was not found.")
        except Exception as exc:
            raise exc

    def upload_object(self, file_path, object_name, extra=None, headers=None):
        """ 
        Upload an object currently located on a disk. 
        https://libcloud.readthedocs.io/en/latest/storage/api.html#libcloud.storage.base.StorageDriver.upload_object
        """
        upload_obj = self.driver.upload_object(file_path, self.container, object_name, extra, headers)
        return upload_obj

    def upload_object_via_stream(self, iterator, object_name, extra=None, headers=None):
        """
        Upload an object using an iterator.
        https://libcloud.readthedocs.io/en/latest/storage/api.html#libcloud.storage.base.StorageDriver.upload_object_via_stream
        """
        storage_obj = self.driver.upload_object_via_stream(iterator, self.container, object_name, extra, headers)
        return storage_obj

    def download_object_via_stream(self, object_name, chunk_size=None):
        """
        Returns an storage object and the iterator which can be used to download it from storage.
        https://libcloud.readthedocs.io/en/latest/storage/api.html#libcloud.storage.base.StorageDriver.download_object_as_stream
        """
        try:
            storage_obj = self.driver.get_object(self.container.name, object_name)
            return storage_obj, self.driver.download_object_as_stream(storage_obj, chunk_size)
        except Exception as exc:
            raise StorageError("Storage.download_object_via_stream - error while downloading " + object_name, exc)

    def delete_object(self, object_name):
        """
        Deletes a storage object, returns true if successfull.
        https://libcloud.readthedocs.io/en/latest/storage/api.html#libcloud.storage.base.StorageDriver.delete_object
        """
        storage_obj = self.driver.get_object(self.container.name, object_name)
        return self.driver.delete_object(storage_obj)
