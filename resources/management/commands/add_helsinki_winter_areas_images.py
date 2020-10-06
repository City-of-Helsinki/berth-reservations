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
            image_file = "/img/helsinki_winter_areas/{}".format(image_filename)

            winter_area.image_file = image_file
            winter_area.save()

            updated_winter_areas += 1

        self.stdout.write(
            "Successfully updated {} winter storage areas".format(updated_winter_areas)
        )

        if missing_images:
            self.stderr.write("Could not find following image files for winter areas:")
            for filename in missing_images:
                self.stderr.write(filename)
