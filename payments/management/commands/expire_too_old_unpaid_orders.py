from django.conf import settings
from django.db.transaction import atomic

from payments.models import Order
from utils.base_expiration_command import FeatureFlagCommand


class Command(FeatureFlagCommand):
    help = 'Sets too old orders from state "waiting" to state "expired".'
    feature_flag_name = "ORDER_EXPIRATION_CRONJOB_ENABLED"

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--include-paper-invoice-customers",
            action="store_true",
            help="includes the paper invoice customers from the queryset",
        )

    @atomic
    def run_operation(self, dry_run, **options) -> int:
        exclude_paper_invoice_customers = not options["include_paper_invoice_customers"]

        return Order.objects.expire_too_old_unpaid_orders(
            settings.EXPIRE_WAITING_ORDERS_OLDER_THAN_DAYS,
            dry_run=dry_run,
            exclude_paper_invoice_customers=exclude_paper_invoice_customers,
        )
