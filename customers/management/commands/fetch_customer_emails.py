import csv
import logging

from django.core.management import BaseCommand

from customers.services import ProfileService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch emails the given list of profile ids."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile-token",
            required=True,
            type=str,
            help="[Required] The API token for Profile",
        )
        parser.add_argument(
            "--input-file",
            required=True,
            type=str,
            help="[Required] Input file containing the list of profile ids to fetch separated by newline",
        )
        parser.add_argument(
            "--output-file",
            required=True,
            type=str,
            help="[Required] Filename for the output",
        )

    def handle(
        self,
        profile_token,
        input_file,
        output_file,
        *args,
        **options,
    ):
        with open(input_file, "r") as ids_file:
            ids = ids_file.read().splitlines()

        profile_service = ProfileService(profile_token=profile_token)
        profiles = profile_service.get_all_profiles(ids)

        with open(output_file, "w") as out_file:
            writer = csv.writer(out_file)
            for profile in profiles.values():
                writer.writerow(
                    [f"{profile.first_name} {profile.last_name}", profile.email]
                )

        self.stdout.write(self.style.SUCCESS(f"Exported Processed {len(ids)} profiles"))
