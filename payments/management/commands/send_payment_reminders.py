from payments.models import Order
from utils.base_expiration_command import FeatureFlagCommand


class Command(FeatureFlagCommand):
    help = "Send payment reminder notifications"
    feature_flag_name = "PAYMENTS_REMINDER_NOTIFICATION_CRONJOB_ENABLED"

    def run_operation(self, dry_run, **options) -> int:
        return Order.objects.send_payment_reminders_for_unpaid_orders(dry_run=dry_run)
