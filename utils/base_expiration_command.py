import logging
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class FeatureFlagCommand(BaseCommand):
    """
    Subclasses must:
    * implement run_operation
    * define feature_flag_name
    * define help: a help text
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run, don't persist any changes",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=f"Run the command even if {self.feature_flag_name} is not set",
        )

    def get_name(self):
        return type(self).__module__.split(".")[-1]

    def setup_logging(self):
        # Output results also to stdout so that the kubernetes cronjob results are available
        logger.addHandler(logging.StreamHandler(sys.stdout))
        logger.setLevel(logging.INFO)

    def handle(self, dry_run, force, *args, **options):
        self.setup_logging()
        if not getattr(settings, self.feature_flag_name) and not force:
            logger.info(f"{self.feature_flag_name} not set, {self.get_name()} disabled")
            return
        logger.info(f"{self.get_name()} starting: {self.help}")
        num_changes = self.run_operation(dry_run, **options)
        if dry_run:
            logger.info(
                f"{self.get_name()}: Dry run, do not save changes. {num_changes} changes were made."
            )
        else:
            logger.info(f"{self.get_name()} done, {num_changes} changes were made.")

    def run_operation(self, dry_run, **options) -> int:
        raise NotImplementedError
