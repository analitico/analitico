# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

import os
import io
import logging
import analitico
import api

from django.utils.crypto import get_random_string
from rest_framework import status
from api.models.drive import *
from .utils import AnaliticoApiTestCase


class DriveTests(AnaliticoApiTestCase):
    """ Test allocating storage on Hetzner storage boxes, etc. """

    drive: Drive = None

    driver: api.libcloud.WebdavStorageDriver = None

    def get_storage_conf(self):
        return {
            "storage": {
                "driver": "hetzner-webdav",
                "storagebox_id": 196_299,
                "url": "https://u208199.your-storagebox.de",
                "credentials": {"username": "u208199", "password": "AyG9OxeeuXr0XpqF"},
            }
        }

    def setUp(self):
        self.setup_basics()
        self.drive = api.models.Drive(id="dr_box002_test", attributes=self.get_storage_conf())
        self.drive.save()
        self.driver = hetzner_webdav_driver(self.drive)

    def test_drive_create_then_delete_directory(self):
        dir_name = "tst_dir_" + get_random_string().lower()
        # create then delete directory
        self.assertEqual(self.driver.exists(dir_name), False)
        self.driver.mkdir(dir_name)
        self.assertEqual(self.driver.exists(dir_name), True)
        self.driver.rmdir(dir_name)
        self.assertEqual(self.driver.exists(dir_name), False)

    def test_drive_create_then_delete_directory_with_contents(self):
        dir_name = "tst_dir_" + get_random_string().lower()
        num_files = len(self.driver.ls("/"))

        self.assertEqual(self.driver.exists(dir_name), False)
        self.driver.mkdir(dir_name)
        self.assertEqual(self.driver.exists(dir_name), True)
        for i in range(0, 10):
            remote_path = os.path.join(dir_name, f"/{dir_name}/pippo-{i}.txt")
            data = io.BytesIO(b"This is some stuff")
            self.driver.upload(data, remote_path)
        self.driver.rmdir(dir_name)
        self.assertEqual(self.driver.exists(dir_name), False)
        self.assertEqual(len(self.driver.ls("/")), num_files)

    def test_drive_refresh_stats(self):
        dr_refresh_stats()

    def test_drive_create_workspace_storage(self):
        delete = False
        try:
            dr_create_workspace_storage(self.ws1)
            delete = True

            self.ws1.refresh_from_db()
            driver = self.ws1.storage.driver
            num_files = len(driver.ls("/"))
            driver.upload(io.BytesIO(b"This is Mickey"), "mickey.txt")
            driver.upload(io.BytesIO(b"This is Goofy"), "goofy.txt")

            # workspace driver
            self.assertTrue(driver.exists("/mickey.txt"))
            self.assertTrue(driver.exists("/goofy.txt"))

            # main storage box driver (different driver one directory up!)
            self.assertTrue(self.driver.exists(f"/{self.ws1.id}/mickey.txt"))
            self.assertTrue(self.driver.exists(f"/{self.ws1.id}/goofy.txt"))

            # delete subaccount and remove its files
            dr_delete_workspace_storage(self.ws1)
            self.ws1.refresh_from_db()
            delete = False

            # main storage box driver (different driver one directory up!)
            self.assertFalse(self.driver.exists(f"/{self.ws1.id}/mickey.txt"))
            self.assertFalse(self.driver.exists(f"/{self.ws1.id}/goofy.txt"))

        except Exception as exc:
            logging.error(exc)
        finally:
            if delete:
                dr_delete_workspace_storage(self.ws1)
