from django.core.management.base import BaseCommand

from api.factory import factory
from api.k8 import k8_build_v2


class Command(BaseCommand):
    def add_arguments(self, parser):
        # https://docs.djangoproject.com/en/2.1/howto/custom-management-commands/
        # https://docs.python.org/3/library/argparse.html#module-argparse
        self.help = "Take a recipe_id followed by a model_it and build a docker of the recipe into the model."
        parser.add_argument("item_id", nargs="*", type=str, help=self.help)

    def handle(self, *args, **options):
        item_id = options["item_id"][0]
        target_id = options["item_id"][1]

        item = factory.get_item(item_id)  # the recipe
        target = factory.get_item(target_id)  # the model

        k8_build_v2(item, target)
        return 0
