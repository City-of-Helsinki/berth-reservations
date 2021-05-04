"""
This command creates or updates Harbor objects based on a JSON
that has the following structure for its items:

"AIRORANTA": {
    "servicemap_id": "40393",
    "berth_count": 11,
    "max_length": 500,
    "max_width": 200
}, ...

"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from ...models import Harbor


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            action="store",
            dest="file",
            help="Path to JSON file with harbors' data",
        )

    def handle(self, **options):
        json_filepath = options["file"]
        if not json_filepath:
            raise CommandError("No path to JSON file provided")

        number_of_created_harbors = 0
        number_of_modified_harbors = 0

        with open(json_filepath, "r") as json_file:
            harbors_dict = json.load(json_file)
            for harbor_name, harbor_data in harbors_dict.items():
                with transaction.atomic():
                    defaults = {
                        "servicemap_id": harbor_data["servicemap_id"],
                        "number_of_places": harbor_data["berth_count"],
                        "maximum_length": harbor_data["max_length"],
                        "maximum_width": harbor_data["max_width"],
                    }
                    harbor, created = Harbor.objects.update_or_create(
                        identifier=slugify(harbor_name), defaults=defaults
                    )

                    if created:
                        number_of_created_harbors += 1
                    else:
                        number_of_modified_harbors += 1

        self.stdout.write("Created {} harbors".format(number_of_created_harbors))
        self.stdout.write("Modified {} harbors".format(number_of_modified_harbors))
