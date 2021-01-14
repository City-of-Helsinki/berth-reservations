import logging
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from payments.models import Order

# FOR TESTING
logger = logging.getLogger(__name__)


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class Command(BaseCommand):
    help = 'Sets too old orders from state "waiting" to state "expired".'

    @atomic
    def handle(self, *args, **options):
        logger.info("Expiring too old unpaid orders...")
        num_of_updated_orders = Order.objects.expire_too_old_unpaid_orders(
            settings.EXPIRE_WAITING_ORDERS_OLDER_THAN_DAYS
        )
        logger.info("Done, {} order(s) got expired.".format(num_of_updated_orders))
