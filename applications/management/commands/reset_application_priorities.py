from django.db.transaction import atomic

from applications.models import BerthApplication
from utils.base_expiration_command import ExpirationCommand


class Command(ExpirationCommand):
    help = "Resets LOW-priority berth applications to MEDIUM-priority"
    feature_flag_name = "BERTH_APPLICATION_PRIORITY_RESET_CRONJOB_ENABLED"

    @atomic
    def run_expiration(self, dry_run):
        return BerthApplication.objects.reset_application_priority(
            only_low_priority=True, dry_run=dry_run,
        )
