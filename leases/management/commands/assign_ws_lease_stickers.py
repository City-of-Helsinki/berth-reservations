from django.core.management import BaseCommand

from applications.enums import ApplicationAreaType
from leases.enums import LeaseStatus
from leases.models import WinterStorageLease
from leases.stickers import get_next_sticker_number


class Command(BaseCommand):

    help = "Assign stickers for existing paid WS leases"

    def handle(self, *args, **options):
        self.stdout.write("Assigning stickers for existing paid WS unmarked leases")

        paid_ws_leases_without_sticker = WinterStorageLease.objects.filter(
            application__area_type=ApplicationAreaType.UNMARKED,
            status=LeaseStatus.PAID,
            sticker_number=None,
        )

        for lease in paid_ws_leases_without_sticker:
            self.stdout.write("Assigning sticker for lease {}".format(lease.id))
            lease.sticker_number = get_next_sticker_number(lease.start_date)
            lease.save()

        self.stdout.write(
            self.style.SUCCESS("Assigning stickers for existing paid WS leases done!")
        )
