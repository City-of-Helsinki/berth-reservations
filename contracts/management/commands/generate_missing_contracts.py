from django.core.management import BaseCommand

from contracts.services import get_contract_service
from leases.models import BerthLease, WinterStorageLease


class Command(BaseCommand):
    help = "Generate contracts for leases in status DRAFTED and OFFERED, which are missing contracts"

    def handle(self, *args, **options):
        winter_storage_leases = WinterStorageLease.objects.filter(contract=None)
        berth_leases = BerthLease.objects.filter(contract=None)

        failed = []
        success_count = 0
        fail_count = 0

        for winter_storage_lease in winter_storage_leases:
            try:
                get_contract_service().create_winter_storage_contract(
                    winter_storage_lease
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to generate contract for ws lease: {winter_storage_lease.id}, exception: {str(e)}"
                    )
                )
                failed.append(
                    f"winter storage lease: {winter_storage_lease.id}, exception: {str(e)}"
                )

        for berth_lease in berth_leases:
            try:
                get_contract_service().create_berth_contract(berth_lease)
                success_count += 1
            except Exception as e:
                fail_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to generate contract for berth lease: {berth_lease.id}, exception: {str(e)}"
                    )
                )
                failed.append(f"berth lease: {berth_lease.id}, exception: {str(e)}")

        if not failed:
            self.stdout.write(
                self.style.SUCCESS(f"Done! Added contracts to {success_count} leases.")
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to generate contracts for the following {fail_count} leases:"
                )
            )
            self.stdout.writelines(failed)
