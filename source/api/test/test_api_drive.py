
# relax pylint on testing code
# pylint: disable=no-member
# pylint: disable=unused-variable
# pylint: disable=unused-wildcard-import

import logging
import analitico
import api

from rest_framework import status

from api.models.drive import Drive, dr_refresh_stats, dr_create_workspace_storage, dr_delete_workspace_storage
from .utils import AnaliticoApiTestCase

class DriveTests(AnaliticoApiTestCase):
    """ Test allocating storage on Hetzner storage boxes, etc. """

    def setUp(self):
        self.setup_basics()
        drive = api.models.Drive(
            id="dr_box002_test",
            attributes={
                "storage": {
                    "driver": "hetzner-webdav",
                    "storagebox_id": 196299,
                    "url": "https://u208199.your-storagebox.de",
                    "credentials": {"username": "u208199", "password": "AyG9OxeeuXr0XpqF"},
                }
            },
        )
        drive.save()

    def test_drive_refresh_stats(self):
        dr_refresh_stats()

    def test_drive_create_workspace_storage(self):
        try:
            dr_create_workspace_storage(self.ws1)
        except Exception as exc:
            logging.error(exc)
        finally:
            dr_delete_workspace_storage(self.ws1)
