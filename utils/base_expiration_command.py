import logging
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class ExpirationCommand(BaseCommand):
    """
    Subclasses must:
    * implement run_expiration
    * define feature_flag_name
    * define operation_name
    * define help: a help text
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run, roll back the transaction at end",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=f"Run the command even if {self.feature_flag_name} is not set",
        )
        parser.add_argument(
            "--include-paper-invoice-customers",
            action="store_true",
            help="includes the paper invoice customers from the queryset",
        )

    def get_name(self):
        return type(self).__module__.split(".")[-1]

    def setup_logging(self):
        # Output results also to stdout so that the kubernetes cronjob results are available
        logger.addHandler(logging.StreamHandler(sys.stdout))
        logger.setLevel(logging.INFO)

    def handle(self, dry_run, force, include_paper_invoice_customers, *args, **options):
        self.setup_logging()
        if not getattr(settings, self.feature_flag_name) and not force:
            logger.info(f"{self.feature_flag_name} not set, {self.get_name()} disabled")
            return
        logger.info(f"{self.get_name()} starting: {self.help}")
        num_changes = self.run_expiration(
            dry_run, include_paper_invoice_customers=include_paper_invoice_customers
        )
        if dry_run:
            logger.info(
                f"{self.get_name()}: Dry run, do not save changes. {num_changes} object(s) would be expired."
            )
        else:
            logger.info(
                f"{self.get_name()} done, {num_changes} object(s) were expired."
            )

    def run_expiration(self, dry_run, **kwargs):
        raise NotImplementedError
