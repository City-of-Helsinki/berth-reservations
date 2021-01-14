import logging
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from payments.models import Order

logger = logging.getLogger(__name__)
# Output results also to stdout so that the kubernetes cronjob results are available
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    help = 'Sets too old orders from state "waiting" to state "expired".'

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run, roll back the transaction at end",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run the command even if ORDER_EXPIRATION_CRONJOB_ENABLED is not set",
        )

    @atomic
    def handle(self, dry_run, force, *args, **options):
        if not settings.ORDER_EXPIRATION_CRONJOB_ENABLED and not force:
            logger.info("ORDER_EXPIRATION_CRONJOB_ENABLED not set, cronjob disabled")
            return
        logger.info("Expiring too old unpaid orders...")
        num_of_updated_orders = Order.objects.expire_too_old_unpaid_orders(
            settings.EXPIRE_WAITING_ORDERS_OLDER_THAN_DAYS, dry_run=dry_run,
        )
        if dry_run:
            logger.info(
                "Dry run, do not save changes. {} order(s) would be expired.".format(
                    num_of_updated_orders
                )
            )
        else:
            logger.info("Done, {} order(s) got expired.".format(num_of_updated_orders))
