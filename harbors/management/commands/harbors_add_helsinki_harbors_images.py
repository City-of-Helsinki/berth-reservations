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
            image_filename = "{}.jpg".format(harbor.servicemap_id)
            image_file = "/img/helsinki_harbors/{}".format(image_filename)

            harbor.image_file = image_file
            harbor.save()

            updated_harbors += 1

        self.stdout.write("Successfully updated {} harbors".format(updated_harbors))

        if missing_images:
            self.stderr.write(
                "Could not find images for harbors with following Servicemap IDs:"
            )
            for id in missing_images:
                self.stderr.write(id)
