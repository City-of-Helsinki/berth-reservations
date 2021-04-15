from typing import Union

from django.core.exceptions import ValidationError
from django.core.management import BaseCommand
from django.db import IntegrityError, transaction

from applications.models import BerthApplication, WinterStorageApplication
from applications.utils import create_or_update_boat_for_application
from leases.consts import ACTIVE_LEASE_STATUSES


class Command(BaseCommand):
    help = "Creates boats for the applications that have already been handled and dealt (have a valid lease)"
    created = 0
    updated = 0
    invalid = 0

    def create_boat(
        self, application: Union[BerthApplication, WinterStorageApplication]
    ):
        # Create or update the boat
        boat, _created = create_or_update_boat_for_application(application)

        # If the application has a lease, assign the boat to the lease
        if application.lease:
            application.lease.boat = boat
            application.lease.save()

        if _created:
            self.created += 1
        else:
            self.updated += 1

    def handle(self, *args, **options):
        berth_applications = BerthApplication.objects.filter(
            lease__status__in=ACTIVE_LEASE_STATUSES
        )
        winter_applications = WinterStorageApplication.objects.filter(
            lease__status__in=ACTIVE_LEASE_STATUSES
        )

        for application in list(berth_applications) + list(winter_applications):
            try:
                with transaction.atomic():
                    self.create_boat(application)
            except (IntegrityError, ValidationError):
                self.invalid += 1

        self.stdout.write(self.style.SUCCESS("Finished creating boats"))
        self.stdout.write(f"Created: {self.created}")
        self.stdout.write(f"Updated: {self.updated}")
        self.stdout.write(self.style.ERROR(f"Invalid: {self.invalid}"))
