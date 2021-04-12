import datetime

import pytest  # noqa
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from leases.enums import LeaseStatus
from payments.enums import OfferStatus
from payments.models import BerthSwitchOffer
from payments.tests.factories import BerthSwitchOfferFactory


@freeze_time("2021-01-09T08:00:00Z")
def test_expire_too_old_offers():
    offer = BerthSwitchOfferFactory(due_date=datetime.date(2021, 1, 2),)
    offer.status = OfferStatus.OFFERED
    offer.save()
    assert (
        BerthSwitchOffer.objects.expire_too_old_offers(older_than_days=7, dry_run=False)
        == 0
    )
    offer.refresh_from_db()
    assert offer.status == OfferStatus.OFFERED
    offer.due_date = datetime.date(2021, 1, 1)
    offer.save()

    assert (
        BerthSwitchOffer.objects.expire_too_old_offers(older_than_days=7, dry_run=False)
        == 1
    )

    offer.refresh_from_db()
    offer.lease.refresh_from_db()
    assert offer.status == OfferStatus.EXPIRED
    assert (
        offer.lease.status == LeaseStatus.PAID
    )  # the customer's previous/existing lease is not changed

    offer.due_date = datetime.datetime(2021, 2, 1)
    with pytest.raises(ValidationError):
        offer.save()
