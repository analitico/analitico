# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

import os
import io
import logging
import analitico
import api
import tempfile
import base64
import time
from pathlib import Path

from django.test import tag
from analitico.utilities import subprocess_run, save_text
from django.utils.crypto import get_random_string
from rest_framework import status
from api.models.drive import *
from .utils import AnaliticoApiTestCase


class DriveTests(AnaliticoApiTestCase):
    """ Test allocating storage on Hetzner storage boxes, etc. """

    driver: api.libcloud.WebdavStorageDriver = None

    def setUp(self):
        self.setup_basics()
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

    @tag("slow", "live")
    def test_drive_create_workspace_storage(self):
        ws_id = "ws_testcreatestorage_" + get_random_string(4)
        ws = Workspace.objects.create(pk=ws_id)
        try:
            dr_create_workspace_storage(ws)

            driver = ws.storage.driver
            num_files = len(driver.ls("/"))
            driver.upload(io.BytesIO(b"This is Mickey"), "mickey.txt")
            driver.upload(io.BytesIO(b"This is Goofy"), "goofy.txt")

            # workspace driver
            self.assertTrue(driver.exists("/mickey.txt"))
            self.assertTrue(driver.exists("/goofy.txt"))

            # main storage box driver (different driver one directory up!)
            self.assertTrue(self.driver.exists(f"/{ws.id}/mickey.txt"))
            self.assertTrue(self.driver.exists(f"/{ws.id}/goofy.txt"))

            # delete subaccount and remove its files
            ws.delete()
            ws = None

            # main storage box driver (different driver one directory up!)
            self.assertFalse(self.driver.exists(f"/{ws_id}/mickey.txt"))
            self.assertFalse(self.driver.exists(f"/{ws_id}/goofy.txt"))

        except Exception as exc:
            logging.error(exc)
            raise exc
        finally:
            if ws:
                ws.delete()

    @tag("slow")
    def test_drive_base_rsync(self):
        delete = False
        try:
            ws = Workspace.objects.create(pk="ws_testrsync" + get_random_string(6))
            dr_create_workspace_storage(ws)
            delete = True

            time.sleep(60)
            # sometimes the storage takes longer to be available
            ws.refresh_from_db()
            driver: api.libcloud.WebdavStorageDriver = ws.storage.driver

            storage_conf = ws.get_attribute("storage")
            username = storage_conf["credentials"]["username"]
            storage_url = f"{username}@{username}.your-storagebox.de"

            # ssh keys
            self.assertIn("ssh_private_key", storage_conf["credentials"])
            self.assertIn("ssh_public_key", storage_conf["credentials"])

            # create id_rsa
            with tempfile.TemporaryDirectory() as d:
                private_key_name = os.path.join(d, "id_rsa")
                signature = storage_conf["credentials"]["ssh_private_key"]
                signature = str(base64.b64decode(signature), "ascii")
                save_text(signature, private_key_name)
                os.chmod(private_key_name, 0o600)

                # sync files from local to remote drive
                # create some file locally
                f1_name = os.path.join(d, analitico.utilities.id_generator() + ".txt")
                save_text("this is a test content", f1_name)
                f2_name = os.path.join(d, analitico.utilities.id_generator() + ".txt")
                save_text("this is another test content", f2_name)

                sync_cmd = [
                    "rsync",
                    "--recursive",
                    "--progress",
                    "-e",
                    f"'ssh -p23 -o StrictHostKeyChecking=no -i {private_key_name}'",
                    f"{d}/",
                    f"{storage_url}:./",
                ]
                subprocess_run(" ".join(sync_cmd), shell=True)

                self.assertTrue(driver.exists(f"/{os.path.basename(f1_name)}"))
                self.assertTrue(driver.exists(f"/{os.path.basename(f2_name)}"))

                # sync files from remote drive to local
                # create some files on storage
                f3_name = analitico.utilities.id_generator() + ".txt"
                driver.upload(io.BytesIO(b"This is Mickey"), f3_name)
                f4_name = analitico.utilities.id_generator() + ".txt"
                driver.upload(io.BytesIO(b"This is Goofy"), f4_name)

                sync_cmd = [
                    "rsync",
                    "--recursive",
                    "--progress",
                    "-e",
                    f"'ssh -p23 -o StrictHostKeyChecking=no -i {private_key_name}'",
                    f"{storage_url}:./",
                    f"{d}/",
                ]
                subprocess_run(" ".join(sync_cmd), shell=True)

                self.assertTrue(Path(os.path.join(d, f3_name)).exists())
                self.assertTrue(Path(os.path.join(d, f4_name)).exists())

        except Exception as exc:
            logging.error(exc)
            raise exc
        finally:
            if delete:
                dr_delete_workspace_storage(ws)
