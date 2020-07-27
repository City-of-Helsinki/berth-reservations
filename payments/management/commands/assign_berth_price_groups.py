from django.core.management import BaseCommand

from payments.models import BerthPriceGroup
from resources.models import BerthType


class Command(BaseCommand):
    help = "Assign all BerthTypes to a BerthPriceGroup if they don't belong to any"

    def handle(self, *args, **options):
        # Get berth types without price group
        berth_types = BerthType.objects.filter(price_group__isnull=True)

        # For every BT:
        #   get_or_create a BPG with the BT width
        #   Assign the price_group to the recovered BPG

        start_groups = BerthPriceGroup.objects.count()
        for berth_type in berth_types:
            group = BerthPriceGroup.objects.get_or_create_for_width(berth_type.width)
            berth_type.price_group = group
            berth_type.save()
        end_groups = BerthPriceGroup.objects.count()

        groups_created = end_groups - start_groups
        self.stdout.write(
            self.style.SUCCESS(
                f"BerthTypes assigned: {len(berth_types)}\n"
                f"BerthPriceGroups created: {groups_created}"
            )
        )
