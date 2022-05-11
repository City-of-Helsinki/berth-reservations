from django.db.transaction import atomic

from applications.models import BerthApplication
from utils.base_expiration_command import FeatureFlagCommand


class Command(FeatureFlagCommand):
    help = "Resets LOW-priority berth applications to MEDIUM-priority"
    feature_flag_name = "BERTH_APPLICATION_PRIORITY_RESET_CRONJOB_ENABLED"

    @atomic
    def run_operation(self, dry_run, **options) -> int:
        return BerthApplication.objects.reset_application_priority(
            only_low_priority=True,
            dry_run=dry_run,
        )
