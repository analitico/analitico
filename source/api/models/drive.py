import collections
import jsonfield
import os
import os.path
import requests
import urllib

# pylint: disable=no-member

from django.db import models
from django.utils.crypto import get_random_string
from rest_framework import status

import analitico
import analitico.plugin
import analitico.utilities
from analitico import AnaliticoException

import api.slack
import api.storage
import api.libcloud

from .items import ItemMixin, ItemAssetsMixin
from .workspace import Workspace

# Credentials used to create subaccounts on Hetzner Storage Boxes
HETZNER_ENDPOINT = "https://robot-ws.your-server.de"
HETZNER_ACCOUNT = os.environ["ANALITICO_HETZNER_ACCOUNT"]
HETZNER_PASSWORD = os.environ["ANALITICO_HETZNER_PASSWORD"]
assert HETZNER_ACCOUNT
assert HETZNER_PASSWORD
assert HETZNER_ENDPOINT.startswith("https://")


def generate_drive_id():
    return analitico.DRIVE_PREFIX + get_random_string(length=6).lower()


class Drive(ItemMixin, ItemAssetsMixin, models.Model):
    """ Configuration for a storage drive, network mount, bucket, etc used to store customer files. """

    # Unique id has a type prefix + random string
    id = models.SlugField(primary_key=True, default=generate_drive_id)

    # Title is text only, does not need to be unique, just descriptive
    title = models.TextField(blank=True)

    # Time when created
    created_at = models.DateTimeField(auto_now_add=True)

    # Time when last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Additional attributes are stored as json (used by AttributeMixin)
    attributes = jsonfield.JSONField(load_kwargs={"object_pairs_hook": collections.OrderedDict}, blank=True, null=True)

    def get_storage(self):
        """ Returns storage configuration for this drive. """
        return self.get_attribute("storage")

    def is_hetzner_storage_box(self):
        return self.get_attribute("storage.driver", None) == "hetzner-webdav"


##
## Utilities
##

# Hetzner Storage Box APIs
# https://robot.your-server.de/doc/webservice/en.html#storage-box


def hetzner_request(url, method="GET", params=None):
    """ 
    Send an API request to Hetzner robot
    https://robot.your-server.de/doc/webservice/en.html#get-storagebox
    """
    url = urllib.parse.urljoin(HETZNER_ENDPOINT, url)
    response = requests.request(method, url, auth=(HETZNER_ACCOUNT, HETZNER_PASSWORD), params=params)
    if response.status_code != 200:
        raise AnaliticoException(
            f"{url} returned status code: {response.status_code}", status_code=response.status_code
        )
    try:
        return response.json()
    except ValueError:
        return None


def hetzner_webdav_driver(item) -> api.libcloud.WebdavStorageDriver:
    """ Create a driver that can operate on the storage drive. """
    storage_conf = item.get_attribute("storage")
    assert storage_conf and storage_conf["driver"] == "hetzner-webdav"
    storage = api.storage.Storage.factory(storage_conf)
    return storage.driver


def dr_refresh_stats(drive: Drive = None):
    """ Update the status of a given storage box (or all). """
    for dr in [drive] if drive else Drive.objects.all():
        # retrieve fresh information on storagebox and its subaccounts
        storagebox_id = dr.get_attribute("storage.storagebox_id")
        json = hetzner_request(f"/storagebox/{storagebox_id}")
        dr.set_attribute("hetzner.storagebox", json["storagebox"])
        json = hetzner_request(f"/storagebox/{storagebox_id}/subaccount")
        dr.set_attribute("hetzner.subaccounts", json)
        dr.save()


def dr_create_workspace_storage(workspace: Workspace, refresh_stats: bool = True) -> bool:
    """ Provision a subaccount on one of our storage boxes and configures it so the workspace can use it as storage. """

    if workspace.get_attribute("storage"):
        raise AnaliticoException(
            f"Workspace {workspace.id} already has its storage configured.", status_code=status.HTTP_400_BAD_REQUEST
        )

    # refresh storageboxes info then choose box with smallest number of customers
    if refresh_stats:
        dr_refresh_stats()

    choosen_subaccounts = None
    choosen_drive = None

    for dr in Drive.objects.all():
        dr_subaccounts = len(dr.get_attribute("hetzner.subaccounts", []))
        if choosen_drive is None or dr_subaccounts < choosen_subaccounts:
            choosen_subaccounts = dr_subaccounts
            choosen_drive = dr
        # TODO could mark a box to take no more customers

    if not choosen_drive:
        raise AnaliticoException(
            "dr_create_workspace_storage - could not find a storage box where the account can be allocated"
        )

    # create directory that should be used by the workspace on this drive
    driver = hetzner_webdav_driver(choosen_drive)
    subaccount_path = f"/{workspace.id}/"
    if not driver.exists(subaccount_path):
        driver.mkdir(subaccount_path)

    # create subaccount on this drive
    storagebox_id = choosen_drive.get_attribute("storage.storagebox_id")
    json = hetzner_request(
        method="POST",
        url=f"/storagebox/{storagebox_id}/subaccount",
        params={
            "homedirectory": workspace.id,  # Homedirectory of the sub-account
            "comment": workspace.id,
            "samba": "true",
            "ssh": "true",
            "webdav": "true",
            "readonly": "false",
        },
    )

    # save subaccount information in the workspace
    subaccount_storage_conf = {
        "driver": "hetzner-webdav",
        "storagebox_id": storagebox_id,
        "drive_id": choosen_drive.id,
        "account_id": json["subaccount"]["accountid"],
        "url": "https://" + json["subaccount"]["server"],
        "credentials": {"username": json["subaccount"]["username"], "password": json["subaccount"]["password"]},
    }
    workspace.set_attribute("storage", subaccount_storage_conf)
    workspace.save()

    # refresh information on drive
    dr_refresh_stats(choosen_drive)
    return True


def dr_delete_workspace_storage(workspace: Workspace) -> bool:
    """ Delete storage associated with workspace.  """
    storage_conf = workspace.get_attribute("storage")
    if not storage_conf or storage_conf["driver"] != "hetzner-webdav":
        raise AnaliticoException(f"Workspace {workspace.id} is not configured as hetzner storage box subaccount")

    drive_id = storage_conf["drive_id"]
    drive = Drive.objects.get(pk=drive_id)
    assert drive

    # delete subaccount on drive
    username = storage_conf["credentials"]["username"]
    storagebox_id = drive.get_attribute("storage.storagebox_id")
    hetzner_request(f"/storagebox/{storagebox_id}/subaccount/{username}", method="DELETE")

    # mount parent account, delete entire directory
    driver = hetzner_webdav_driver(drive)
    subaccount_path = f"/{workspace.id}/"
    if driver.exists(subaccount_path):
        try:
            driver.rmdir(subaccount_path)
        except Exception as exc:
            analitico.logger.warning(
                f"dr_delect_workspace_storage - cannot delete {subaccount_path} on {drive_id}, exception: {exc}"
            )

    # remove storage configuration from workspace
    workspace.set_attribute("storage", None)
    workspace.save()
    return True