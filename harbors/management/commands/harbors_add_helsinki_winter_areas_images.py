import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.translation import activate

from ...models import WinterStorageArea


class Command(BaseCommand):
    def handle(self, **options):
        updated_winter_areas = 0
        missing_images = []

        activate("fi")

        unicode_to_ascii_map = {ord("ö"): "o", ord("ä"): "a", ord("å"): "a"}

        for winter_area in WinterStorageArea.objects.all():
            if not winter_area.name:
                continue

            area_ascii_lowercase_name = (
                winter_area.name.lower()
                .replace(" ", "-")
                .translate(unicode_to_ascii_map)
            )
            image_filename = "{}.jpg".format(area_ascii_lowercase_name)
            absolute_file_path = os.path.join(
                settings.STATIC_ROOT,
                "img/helsinki_winter_areas/{}".format(image_filename),
            )

            if not os.path.isfile(absolute_file_path):
                missing_images.append(image_filename)
                continue

            self.stdout.write("Assigning image for harbor {}".format(winter_area.name))

            with open(absolute_file_path, "rb") as f:
                file_obj = File(f, name=image_filename)
                winter_area.image_file.save(image_filename, file_obj, True)

            updated_winter_areas += 1

        self.stdout.write(
            "Successfully updated {} winter storage areas".format(updated_winter_areas)
        )

        if missing_images:
            self.stderr.write("Could not find following image files for winter areas:")
            for filename in missing_images:
                self.stderr.write(filename)
