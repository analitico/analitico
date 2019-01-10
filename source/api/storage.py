
import django.conf

from rest_framework.exceptions import NotFound

from pprint import pprint

import libcloud
import libcloud.storage.base
import libcloud.storage.types

from libcloud.storage.drivers.google_storage import GoogleStorageDriver

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


    def factory(settings: dict):
        """ Creates a storage object from a settings dictionary or from default settings if None passed. """
        if settings is None:
            settings = django.conf.settings.ANALITICO_STORAGE
        driver = settings['driver']
        credentials = settings['credentials']

        if driver == 'google-storage':
            return Storage(settings, GoogleStorageDriver(**credentials))
        # TODO add other cloud providers as we need them

        raise NotFound("Storage driver '" + driver + "' was not found.")
    factory = staticmethod(factory)

