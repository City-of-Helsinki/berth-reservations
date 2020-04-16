from datetime import date, timedelta

import pytest
from dateutil.utils import today
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from customers.tests.factories import BoatFactory

from ..enums import LeaseStatus
from ..models import (
    BerthLease,
    BerthLeaseChange,
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
    WinterStorageLease,
    WinterStorageLeaseChange,
)
from .factories import BerthLeaseFactory, WinterStorageLeaseFactory


def test_berth_lease_model(berth_lease):
    assert BerthLease.objects.count() == 1


@freeze_time("2020-01-01T08:00:00Z")
def test_berth_lease_before_season():
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    assert start_date == date(year=2020, month=6, day=10)
    assert end_date == date(year=2020, month=9, day=14)


@freeze_time("2020-06-10T08:00:00Z")
def test_berth_lease_start_of_season():
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    assert start_date == date(year=2020, month=6, day=10)
    assert end_date == date(year=2020, month=9, day=14)


@freeze_time("2020-08-01T08:00:00Z")
def test_berth_lease_during_season():
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    assert start_date == date(year=2020, month=8, day=1)
    assert end_date == date(year=2020, month=9, day=14)


@freeze_time("2020-09-14T08:00:00Z")
def test_berth_lease_end_of_season():
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    assert start_date == date(year=2021, month=6, day=10)
    assert end_date == date(year=2021, month=9, day=14)


@freeze_time("2020-11-11T08:00:00Z")
def test_berth_lease_after_season():
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    assert start_date == date(year=2021, month=6, day=10)
    assert end_date == date(year=2021, month=9, day=14)


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


@freeze_time("2020-11-11T08:00:00Z")
def test_lease_should_be_the_same_year():
    start_date = calculate_berth_lease_start_date()
    start_date = start_date.replace(year=start_date.year - 1)
    end_date = calculate_berth_lease_end_date()

    with pytest.raises(ValidationError) as exception:
        BerthLeaseFactory(start_date=start_date, end_date=end_date)

    assert "BerthLease start and end year have to be the same" in str(exception.value)


@freeze_time("2020-11-11T08:00:00Z")
def test_berth_lease_start_should_be_before_end():
    start_date = calculate_berth_lease_end_date()
    end_date = calculate_berth_lease_start_date()

    with pytest.raises(ValidationError) as exception:
        BerthLeaseFactory(start_date=start_date, end_date=end_date)

    assert "Lease start date cannot be after end date" in str(exception.value)


@freeze_time("2020-11-11T08:00:00Z")
def test_winter_storage_lease_start_should_be_before_end():
    start_date = calculate_berth_lease_end_date()
    end_date = calculate_berth_lease_start_date()

    with pytest.raises(ValidationError) as exception:
        WinterStorageLeaseFactory(start_date=start_date, end_date=end_date)

    assert "Lease start date cannot be after end date" in str(exception.value)


@freeze_time("2020-01-01T08:00:00Z")
def test_berth_leases_should_not_overlap(berth):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    # Lease valid for a month starting at the beginning of the season
    BerthLeaseFactory(
        berth=berth,
        start_date=start_date,
        end_date=start_date.replace(month=start_date.month + 1),
    )

    with pytest.raises(ValidationError) as exception:
        BerthLeaseFactory(berth=berth, start_date=start_date, end_date=end_date)

    assert "Berth already has a lease" in str(exception.value)


@freeze_time("2020-01-01T08:00:00Z")
def test_winter_storage_leases_should_not_overlap(winter_storage_place):
    start_date = today()
    end_date = start_date.replace(month=start_date.month + 2)

    # Lease valid for a month starting at the beginning of the season
    WinterStorageLeaseFactory(
        place=winter_storage_place,
        start_date=start_date,
        end_date=start_date.replace(month=start_date.month + 1),
    )

    with pytest.raises(ValidationError) as exception:
        WinterStorageLeaseFactory(
            place=winter_storage_place, start_date=start_date, end_date=end_date
        )

    assert "WinterStoragePlace already has a lease" in str(exception.value)


def test_berth_lease_inactive_berth_raises_error(berth):
    berth.is_active = False
    berth.save()

    with pytest.raises(ValidationError) as exception:
        BerthLeaseFactory(berth=berth)

    assert "Selected berth is not active" in str(exception.value)


def test_winter_storage_lease_inactive_winter_storage_raises_error(
    winter_storage_place,
):
    winter_storage_place.is_active = False
    winter_storage_place.save()

    with pytest.raises(ValidationError) as exception:
        WinterStorageLeaseFactory(place=winter_storage_place)

    assert "Selected place is not active" in str(exception.value)


def test_berth_lease_cannot_update_berth(berth_lease, berth):
    assert BerthLease.objects.get(id=berth_lease.id).berth != berth

    with pytest.raises(ValidationError) as exception:
        berth_lease.berth = berth
        berth_lease.save()

    assert "Cannot change the berth assigned to this lease" in str(exception.value)


def test_winter_storage_lease_cannot_update_place(
    winter_storage_lease, winter_storage_place
):
    assert (
        WinterStorageLease.objects.get(id=winter_storage_lease.id).place
        != winter_storage_place
    )

    with pytest.raises(ValidationError) as exception:
        winter_storage_lease.place = winter_storage_place
        winter_storage_lease.save()

    assert "Cannot change the place assigned to this lease" in str(exception.value)
