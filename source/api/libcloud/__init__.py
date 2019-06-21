from .webdavdrivers import WebdavStorageDriver, WebdavException, metadata_to_amz_meta_headers

# register driver so user can find
from libcloud.compute.providers import set_driver

# set_driver('webdav', 'api.libcloud.webdavdrivers', 'WebdavStorageDriver')
set_driver("webdav", "api.libcloud", "WebdavStorageDriver")
