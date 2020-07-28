import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db.models import Q

from ...models import Harbor


class Command(BaseCommand):
    def handle(self, **options):
        updated_harbors = 0
        missing_images = []

        for harbor in Harbor.objects.exclude(
            Q(servicemap_id=None) | Q(servicemap_id="")
        ):
            self.stdout.write(
                "Assigning image for harbor with servicemap ID {}".format(
                    harbor.servicemap_id
                )
            )
            image_filename = "{}.jpg".format(harbor.servicemap_id)
            absolute_file_path = os.path.join(
                settings.STATIC_ROOT, "img/helsinki_harbors/{}".format(image_filename)
            )

            if not os.path.isfile(absolute_file_path):
                missing_images.append(harbor.servicemap_id)
                continue

            with open(absolute_file_path, "rb") as f:
                file_obj = File(f, name=image_filename)
                harbor.image_file.save(image_filename, file_obj, True)

            updated_harbors += 1

        self.stdout.write("Successfully updated {} harbors".format(updated_harbors))

        if missing_images:
            self.stderr.write(
                "Could not find images for harbors with following Servicemap IDs:"
            )
            for id in missing_images:
                self.stderr.write(id)
