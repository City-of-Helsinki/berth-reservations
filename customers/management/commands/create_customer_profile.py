import logging

from django.core.management import BaseCommand

from customers.exceptions import ProfileServiceException
from customers.services import ProfileService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Utility command to create a CustomerProfile both on Profiili and Vene's backend"

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile-token",
            nargs="?",
            type=str,
            help="[Required] The API token for Profile",
        )
        parser.add_argument(
            "--first-name",
            nargs="?",
            type=str,
            help="[Required] Customer's first name",
        )
        parser.add_argument(
            "--last-name", nargs="?", type=str, help="[Required] Customer's last name",
        )
        parser.add_argument(
            "--email", nargs="?", type=str, help="Customer's email address",
        )
        parser.add_argument(
            "--phone", nargs="?", type=str, help="Customer's phone number",
        )

    def handle(
        self,
        profile_token=None,
        first_name=None,
        last_name=None,
        email=None,
        phone=None,
        *args,
        **options,
    ):
        if not profile_token:
            self.stderr.write(self.style.ERROR("Missing required profile token"))
            return

        if not first_name and not last_name:
            self.stderr.write(
                self.style.ERROR("Cannot create a customer without first and last name")
            )
            return

        profile_service = ProfileService(profile_token=profile_token)
        profile = None
        try:
            profile = profile_service.create_profile(
                first_name, last_name, email, phone
            )
        except ProfileServiceException as e:
            self.stderr.write(self.style.ERROR(str(e)))

        if profile:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created profile for {last_name}, {first_name} ({email})"
                )
            )
            self.stdout.write(f"Profile ID: {profile.id}")
