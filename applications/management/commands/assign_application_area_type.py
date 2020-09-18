from datetime import date

from django.core.management import BaseCommand

from applications.enums import ApplicationAreaType
from applications.models import WinterStorageApplication


class Command(BaseCommand):
    help = "Assign Application area_type for existing applications"

    def handle(self, *args, **options):
        # Get ws applications created after 14.9.2020
        new_applications = WinterStorageApplication.objects.filter(
            created_at__gt=date(2020, 9, 14)
        )

        for application in new_applications:
            application.area_type = application.resolve_area_type()
            application.save()

        # Set applications created before 14.9.2020 as MARKED
        WinterStorageApplication.objects.filter(
            created_at__lte=date(2020, 9, 14)
        ).update(area_type=ApplicationAreaType.MARKED)

        self.stdout.write(self.style.SUCCESS("done!"))
