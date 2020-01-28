from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError

from customers.tests.factories import BoatFactory

from ..enums import LeaseStatus
from ..models import (
    BerthLease,
    BerthLeaseChange,
    WinterStorageLease,
    WinterStorageLeaseChange,
)
from .factories import BerthLeaseFactory


def test_berth_lease_model(berth_lease):
    assert BerthLease.objects.count() == 1


def test_berth_lease_status_changes_are_tracked(berth_lease):
    assert BerthLeaseChange.objects.count() == 0

    berth_lease.status = LeaseStatus.EXPIRED
    berth_lease.save()

    assert BerthLeaseChange.objects.count() == 1


def test_other_lease_changes_are_not_tracked(berth_lease):
    assert BerthLeaseChange.objects.count() == 0

    berth_lease.end_date = berth_lease.end_date + timedelta(days=1)
    berth_lease.save()

    assert BerthLeaseChange.objects.count() == 0


def test_winter_storage_lease_model(winter_storage_lease):
    assert WinterStorageLease.objects.count() == 1


def test_winter_storage_lease_status_changes_are_tracked(winter_storage_lease):
    assert WinterStorageLeaseChange.objects.count() == 0

    winter_storage_lease.status = LeaseStatus.EXPIRED
    winter_storage_lease.save()

    assert WinterStorageLeaseChange.objects.count() == 1


def test_lease_should_have_boat_owner_as_customer():
    another_customers_boat = BoatFactory()
    with pytest.raises(ValidationError):
        BerthLeaseFactory(boat=another_customers_boat)
