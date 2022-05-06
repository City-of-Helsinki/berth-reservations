from django.conf import settings
from django.db.transaction import atomic

from payments.models import Order
from utils.base_expiration_command import ExpirationCommand


class Command(ExpirationCommand):
    help = 'Sets too old orders from state "waiting" to state "expired".'
    feature_flag_name = "ORDER_EXPIRATION_CRONJOB_ENABLED"

    @atomic
    def run_expiration(self, dry_run, **kwargs):
        exclude_paper_invoice_customers = (
            not kwargs["include_paper_invoice_customers"]
            if "include_paper_invoice_customers" in kwargs
            else True
        )
        Order.objects.expire_too_old_unpaid_orders(
            settings.EXPIRE_WAITING_ORDERS_OLDER_THAN_DAYS,
            dry_run=dry_run,
            exclude_paper_invoice_customers=exclude_paper_invoice_customers,
        )
