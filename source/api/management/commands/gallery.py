import os
import requests
import shutil
import yaml
import re
import tempfile

from collections import OrderedDict
from django.core.management.base import BaseCommand
from pathlib import Path

import analitico
import analitico.utilities
import api.models

from analitico import logger
from analitico.utilities import save_text, comma_separated_to_array

# ./publish.py
#
# Publish tutorials from analitico-sdk to analitico-site
# where they can be built into the static pages that are
# then served with analitico's website gallery.

# analitico-site repo should be checked out next to analitico
src_repos = Path(__file__).parent.parent.parent.parent.parent.parent

src_tutorials = (src_repos / "analitico/sdk/tutorials/").resolve()
dst_tutorials = (src_repos / "analitico-site/docs/_tutorials/").resolve()
dst_avatars = (src_repos / "analitico-site/docs/assets/avatars").resolve()
assert src_tutorials.is_dir()
assert dst_tutorials.is_dir()
assert dst_avatars.is_dir()


class Command(BaseCommand):
    def publish_item(self, item):
        """ Take a live item from the gallery and publish as static data to analitico-site. """
        assert item.title, f"{item.id} does not have a title"
        assert item.description, f"{item.id} does not have a description"

        item_config = {
            "id": item.id,
            "type": item.type,
            "date": item.created_at,
            "title": item.title,
            "description": item.description,
            "tags": comma_separated_to_array(item.get_attribute("tags", "")),
            "published": item.get_attribute_as_bool("published"),
            "position": int(item.get_attribute("position", 1000)),
        }

        logger.info(f"{item.id}, published? {item_config['published']}")

        # copy avatar.jpg to avatars/item_id.jpg
        item.download("avatar.jpg", dst_avatars / f"{item.id}.jpg")
        item_config["image"] = f"/assets/avatars/{item.id}.jpg"

        # copy markdown with tutorial description
        with tempfile.NamedTemporaryFile(suffix=".markdown") as f:
            item.download("readme.md", f.name)
            item_markdown = analitico.utilities.read_text(f.name)
        item_yaml = yaml.dump(item_config, Dumper=yaml.Dumper)
        item_markdown = f"---\n{item_yaml}\n---\n{item_markdown}"
        analitico.utilities.save_text(item_markdown, dst_tutorials / (item.id + ".markdown"))

    def handle(self, *args, **options):
        logger.info("gallery - publishing tutorials...")

        # first we should wipe all tutorials from the repo
        shutil.rmtree(dst_tutorials)
        os.makedirs(dst_tutorials)

        # publish tutorials from the live gallery
        for item_class in (api.models.Dataset, api.models.Recipe, api.models.Notebook):
            items = item_class.objects.filter(workspace__id="ws_gallery").all()
            for item in items:
                try:
                    self.publish_item(item)
                except Exception as exc:
                    logger.error(f"An error occoured while publishing {item.id}, exc: {exc}")

        return 0
