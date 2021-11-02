from django.conf import settings
from django.db.transaction import atomic

from utils import base_expiration_command

from ...models import BerthSwitchOffer


class Command(base_expiration_command.ExpirationCommand):
    help = 'Sets too old offers from state "offered" to state "expired".'
    feature_flag_name = "OFFER_EXPIRATION_CRONJOB_ENABLED"

    @atomic
    def run_expiration(self, dry_run):
        return BerthSwitchOffer.objects.expire_too_old_offers(
            settings.EXPIRE_WAITING_OFFERS_OLDER_THAN_DAYS,
            dry_run=dry_run,
        )
