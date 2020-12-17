from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef

from contracts.models import VismaBerthContract
from leases.models import BerthLease


class Command(BaseCommand):
    help = "Fixes broken renewed lease contracts"

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                future_leases = BerthLease.objects.filter(
                    start_date__year=2021,
                    berth=OuterRef("berth"),
                    customer=OuterRef("customer"),
                    contract__isnull=True,
                )

                renewed_leases = BerthLease.objects.filter(
                    Exists(future_leases.values("pk"))
                ).filter(start_date__year=2020, end_date__year=2020,)

                for old_lease in renewed_leases:
                    new_lease = future_leases.get(
                        customer=old_lease.customer,
                        boat=old_lease.boat,
                        start_date__year=2021,
                    )

                    contract_copy = VismaBerthContract.objects.get(lease=old_lease)
                    contract_copy.pk = None
                    contract_copy.save()

                    new_lease.contract = contract_copy
                    new_lease.save()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to fix contracts for renewed leases: {str(e)}"
                )
            )
