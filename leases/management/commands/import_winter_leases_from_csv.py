import csv
import logging
from collections import namedtuple
from datetime import date

from dateutil.utils import today
from django.core.exceptions import ValidationError
from django.core.management import BaseCommand
from django.db import transaction

from customers.exceptions import MultipleProfilesException, NoProfilesException
from customers.models import Boat, CustomerProfile
from customers.services import ProfileService
from leases.enums import LeaseStatus
from leases.models import WinterStorageLease
from resources.models import BoatType, WinterStoragePlace

logger = logging.getLogger(__name__)

LeaseInput = namedtuple(
    "LeaseInput",
    (
        "section_id",
        "place_number",
        "name",
        "email",
        "phone",
        "boat_width",
        "boat_length",
        "boat_register",
        "comment",
    ),
)


class Command(BaseCommand):
    profile_service: ProfileService

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile-token",
            nargs="?",
            type=str,
            help="[Required] The API token for Profile",
        )
        parser.add_argument(
            "--lease-file-path",
            nargs="?",
            type=str,
            help="[Required] The file to parse",
        )

    def get_or_create_customer_profile(
        self, name: str, email: str = None, phone: str = None
    ) -> CustomerProfile:
        names = name.split(" ")
        first_name = names.pop().capitalize()
        last_name = " ".join([name.capitalize() for name in names])

        try:
            helsinki_profile = self.profile_service.find_profile(
                first_name, last_name, email, phone, force_only_one=True
            )
            profile = CustomerProfile.objects.get(id=helsinki_profile.id)
        except (NoProfilesException, CustomerProfile.DoesNotExist):
            logger.debug(f"Creating profile for {last_name}, {first_name} ({email})")
            profile = self.profile_service.create_profile(
                first_name, last_name, email, phone
            )
        return profile

    def get_or_create_boat(
        self, lease_input: LeaseInput, customer_profile: CustomerProfile
    ):
        """First try to match a boat belonging to the customer with the given
        registration number. If it's not found, then it tries finding or creating one
        based on the dimensions."""
        boat = Boat.objects.filter(
            owner=customer_profile, registration_number=lease_input.boat_register
        ).first()

        if boat is None and lease_input.boat_width and lease_input.boat_length:
            boat, _created = Boat.objects.get_or_create(
                owner=customer_profile,
                boat_type=self.OTHER_BOAT_TYPE,
                width=lease_input.boat_width.replace(",", "."),
                length=lease_input.boat_length.replace(",", "."),
                defaults={"registration_number": lease_input.boat_register},
            )
        return boat

    def handle(self, *args, profile_token=None, lease_file_path=None, **options):
        self.profile_service = ProfileService(profile_token=profile_token)
        self.OTHER_BOAT_TYPE = BoatType.objects.get(id=9)

        multiple_profiles = []
        successful = []
        failed = []

        with open(lease_file_path, "r", encoding="utf-8-sig") as cf:
            rd = csv.reader(cf, delimiter=";")
            for line in rd:
                with transaction.atomic():
                    lease_input = LeaseInput(*line)
                    try:
                        customer_profile = self.get_or_create_customer_profile(
                            lease_input.name,
                            email=lease_input.email,
                            phone=lease_input.phone,
                        )
                    except MultipleProfilesException as e:
                        multiple_profiles.append(
                            (
                                lease_input.section_id,
                                lease_input.place_number,
                                lease_input.name,
                                ";".join(e.ids),
                            )
                        )
                        continue

                    try:
                        place = WinterStoragePlace.objects.get(
                            winter_storage_section_id=lease_input.section_id,
                            number=lease_input.place_number,
                        )

                        boat = self.get_or_create_boat(lease_input, customer_profile)
                        comment = ""
                        if lease_input.comment:
                            comment = f"{lease_input.comment}\n"
                        comment += f"Lease imported on {today().date()}"

                        lease = WinterStorageLease.objects.create(
                            customer=customer_profile,
                            place=place,
                            boat=boat,
                            start_date=date(day=15, month=9, year=2020),
                            end_date=date(day=10, month=6, year=2021),
                            status=LeaseStatus.PAID,
                            comment=comment,
                        )
                        successful.append(
                            (
                                str(lease.id),
                                lease_input.section_id,
                                lease_input.place_number,
                                lease_input.name,
                            )
                        )
                    except (WinterStoragePlace.DoesNotExist, ValidationError) as e:
                        failed.append(
                            (
                                lease_input.section_id,
                                lease_input.place_number,
                                lease_input.name,
                                str(e),
                            )
                        )

        with open("./successful_leases.csv", "w+", encoding="utf-8") as successful_file:
            writer = csv.writer(successful_file, delimiter=",")
            writer.writerow(["Lease id", "Section id", "Place number", "Customer name"])
            writer.writerows(successful)

        with open("./multiple_profiles.csv", "w+", encoding="utf-8") as multiple_file:
            writer = csv.writer(multiple_file, delimiter=",")
            writer.writerow(
                ["Section id", "Place number", "Customer name", "Returned ids"]
            )
            writer.writerows(multiple_profiles)

        with open("./failed_leases.csv", "w+", encoding="utf-8") as failed_file:
            writer = csv.writer(failed_file, delimiter=",")
            writer.writerow(["Section id", "Place number", "Customer name", "Error"])
            writer.writerows(failed)
