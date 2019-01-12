
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
#   "container": "data.analitico.ai",
#   "basepath": "",
#   "credentials": {
#     "key": "analitico-api@appspot.gserviceaccount.com",
#     "secret": "-----BEGIN PRIVATE KEY-----\nCggEAI8sbbUa ... WeDeE=\n-----END PRIVATE KEY-----",
#     "project": "analitico-api"
#   }
# }

# Apache Libcloud
# https://libcloud.apache.org

# Storage base APIs
# https://libcloud.readthedocs.io/en/latest/storage/api.html

# Google Storage driver
# https://libcloud.readthedocs.io/en/latest/storage/drivers/google_storage.html

class Storage():
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
            self.container = driver.get_container(settings['container'])
        except libcloud.storage.types.ContainerDoesNotExistError:
            self.container = driver.create_container(settings['container'])            


    @staticmethod
    def factory(settings: dict):
        """ Creates a storage object from a settings dictionary or from default settings if None passed. """
        if settings is None:
            settings = django.conf.settings.ANALITICO_STORAGE
        if 'credentials' not in settings and settings['driver'] == django.conf.settings.ANALITICO_STORAGE['driver']:
            settings['credentials'] = django.conf.settings.ANALITICO_STORAGE['credentials']

        driver = settings['driver']
        credentials = settings['credentials']
        assert driver
        assert credentials

        if driver == 'google-storage':
            driver = libcloud.storage.drivers.google_storage.GoogleStorageDriver(**credentials)
            return Storage(settings, driver)
            
        # TODO add other cloud providers as we need them
        raise NotFound("Storage.factory - driver for '" + driver + "' was not found.")


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
        upload_obj = self.driver.upload_object_via_stream(iterator, self.container, object_name, extra, headers)
        return upload_obj
