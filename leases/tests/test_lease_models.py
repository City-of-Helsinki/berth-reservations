from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from applications.tests.factories import (
    BerthApplicationFactory,
    WinterStorageApplicationFactory,
)
from berth_reservations.tests.factories import CustomerProfileFactory
from customers.tests.factories import BoatFactory

from ..consts import ACTIVE_LEASE_STATUSES
from ..enums import LeaseStatus
from ..models import (
    BerthLease,
    BerthLeaseChange,
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
    WinterStorageLease,
    WinterStorageLeaseChange,
)
from ..utils import (
    calculate_winter_storage_lease_end_date,
    calculate_winter_storage_lease_start_date,
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
    assert (
        winter_storage_lease.start_date == calculate_winter_storage_lease_start_date()
    )
    assert winter_storage_lease.end_date == calculate_winter_storage_lease_end_date()


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
    start_date = date.today()
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


def test_berth_lease_update_application(berth_lease, customer_profile):
    first_application = BerthApplicationFactory(customer=customer_profile)
    second_application = BerthApplicationFactory(customer=customer_profile)

    berth_lease.application = first_application
    berth_lease.save()

    assert BerthLease.objects.get(id=berth_lease.id).application == first_application

    berth_lease.application = second_application
    berth_lease.save()

    assert BerthLease.objects.get(id=berth_lease.id).application == second_application


def test_berth_lease_remove_application(berth_lease, berth_application):
    berth_lease.application = berth_application
    berth_lease.save()

    assert BerthLease.objects.get(id=berth_lease.id).application == berth_application

    berth_lease.application = None
    berth_lease.save()

    assert BerthLease.objects.get(id=berth_lease.id).application is None


def test_berth_lease_update_application_different_customer(berth_lease):
    first_application = BerthApplicationFactory(customer=CustomerProfileFactory())
    second_application = BerthApplicationFactory(customer=CustomerProfileFactory())

    berth_lease.application = first_application
    berth_lease.save()

    assert BerthLease.objects.get(id=berth_lease.id).application == first_application

    with pytest.raises(ValidationError) as exception:
        berth_lease.application = second_application
        berth_lease.save()

    assert (
        "Cannot change the application to one which belongs to another customer"
        in str(exception.value)
    )


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


def test_winter_storage_lease_application_different_customer(winter_storage_lease):
    first_application = WinterStorageApplicationFactory(
        customer=CustomerProfileFactory()
    )
    second_application = WinterStorageApplicationFactory(
        customer=CustomerProfileFactory()
    )

    winter_storage_lease.application = first_application
    winter_storage_lease.save()

    assert (
        WinterStorageLease.objects.get(id=winter_storage_lease.id).application
        == first_application
    )

    with pytest.raises(ValidationError) as exception:
        winter_storage_lease.application = second_application
        winter_storage_lease.save()

    assert (
        "Cannot change the application to one which belongs to another customer"
        in str(exception.value)
    )


@pytest.mark.parametrize("status", ACTIVE_LEASE_STATUSES)
@freeze_time("2020-01-01T08:00:00Z")
def test_berth_lease_is_active_before_season(status):
    lease = BerthLeaseFactory(status=status)

    assert BerthLease.objects.get(id=lease.id).is_active


@freeze_time("2020-07-10T08:00:00Z")
def test_berth_lease_is_active_during_season():
    lease = BerthLeaseFactory(status=LeaseStatus.PAID)

    assert BerthLease.objects.get(id=lease.id).is_active


@freeze_time("2020-01-01T08:00:00Z")
def test_berth_lease_is_not_active_status():
    lease = BerthLeaseFactory(status=LeaseStatus.EXPIRED)

    assert not BerthLease.objects.get(id=lease.id).is_active


@freeze_time("2020-07-10T08:00:00Z")
def test_berth_lease_is_not_active_before_today():
    today = date.today()
    start_date = today.replace(day=today.day - 5)
    end_date = today.replace(day=today.day - 1)
    lease = BerthLeaseFactory(
        status=LeaseStatus.PAID, start_date=start_date, end_date=end_date
    )

    assert not BerthLease.objects.get(id=lease.id).is_active


@freeze_time("2020-07-10T08:00:00Z")
def test_berth_lease_is_not_active_after_today():
    start_date = date(year=2020, month=7, day=11)
    lease = BerthLeaseFactory(status=LeaseStatus.PAID, start_date=start_date)
    assert not BerthLease.objects.get(id=lease.id).is_active


@freeze_time("2020-06-01T08:00:00Z")
def test_winter_storage_lease_is_active_before_season():
    lease = WinterStorageLeaseFactory(status=LeaseStatus.PAID)

    assert WinterStorageLease.objects.get(id=lease.id).is_active


@freeze_time("2020-10-01T08:00:00Z")
def test_winter_storage_lease_is_active_during_season():
    lease = WinterStorageLeaseFactory(status=LeaseStatus.PAID)

    assert WinterStorageLease.objects.get(id=lease.id).is_active


@freeze_time("2020-10-01T08:00:00Z")
def test_winter_storage_lease_is_not_active_status():
    lease = WinterStorageLeaseFactory(status=LeaseStatus.EXPIRED)

    assert not WinterStorageLease.objects.get(id=lease.id).is_active


@freeze_time("2020-10-01T08:00:00Z")
def test_winter_storage_lease_is_not_active_before_today():
    today = date.today()
    start_date = today - relativedelta(days=5)
    end_date = today - relativedelta(days=1)
    lease = WinterStorageLeaseFactory(
        status=LeaseStatus.PAID, start_date=start_date, end_date=end_date
    )

    assert not WinterStorageLease.objects.get(id=lease.id).is_active


@freeze_time("2020-10-10T08:00:00Z")
def test_winter_storage_lease_is_active_today():
    start_date = date.today()
    lease = WinterStorageLeaseFactory(status=LeaseStatus.PAID, start_date=start_date)
    assert WinterStorageLease.objects.get(id=lease.id).is_active


def test_winter_storage_lease_assign_section(winter_storage_section):
    lease = WinterStorageLeaseFactory(place=None, section=winter_storage_section)

    assert lease.section == winter_storage_section
    assert lease.place is None


def test_winter_storage_lease_section_can_have_multiple_leases(winter_storage_section):
    WinterStorageLeaseFactory(place=None, section=winter_storage_section)
    WinterStorageLeaseFactory(place=None, section=winter_storage_section)
    WinterStorageLeaseFactory(place=None, section=winter_storage_section)

    assert winter_storage_section.leases.count() == 3


def test_winter_storage_lease_assign_section_and_place_raises_error(
    winter_storage_place, winter_storage_section
):
    with pytest.raises(ValidationError) as exception:
        WinterStorageLeaseFactory(
            place=winter_storage_place, section=winter_storage_section
        )

    error_msg = str(exception.value)
    assert "Lease cannot have both place and section assigned" in error_msg


def test_winter_storage_lease_assign_no_section_or_place_raises_error():
    with pytest.raises(ValidationError) as exception:
        WinterStorageLeaseFactory(place=None, section=None)

    error_msg = str(exception.value)
    assert "Lease must have either place or section assigned" in error_msg


def test_winter_storage_lease_one_lease_per_place(winter_storage_place):
    WinterStorageLeaseFactory(place=winter_storage_place)

    with pytest.raises(ValidationError) as exception:
        WinterStorageLeaseFactory(place=winter_storage_place)

    error_msg = str(exception.value)
    assert "WinterStoragePlace already has a lease" in error_msg


def test_berth_lease_one_lease_per_place(berth):
    BerthLeaseFactory(berth=berth)

    with pytest.raises(ValidationError) as exception:
        BerthLeaseFactory(berth=berth)

    error_msg = str(exception.value)
    assert "Berth already has a lease" in error_msg


def test_berth_lease_overlapping_leases_start(berth):
    BerthLeaseFactory(berth=berth, start_date="2020-06-10", end_date="2020-09-14")

    with pytest.raises(ValidationError) as exception:
        # The start date of the second lease overlaps with the end date of the existing lease
        BerthLeaseFactory(berth=berth, start_date="2020-08-01", end_date="2020-12-31")

    error_msg = str(exception.value)
    assert "Berth already has a lease" in error_msg


def test_berth_lease_overlapping_leases_end(berth):
    BerthLeaseFactory(berth=berth, start_date="2020-06-10", end_date="2020-09-14")

    with pytest.raises(ValidationError) as exception:
        # The end date of the second lease overlaps with the start date of the existing lease
        BerthLeaseFactory(berth=berth, start_date="2020-01-01", end_date="2020-07-01")

    error_msg = str(exception.value)
    assert "Berth already has a lease" in error_msg


def test_berth_lease_overlapping_leases_start_and_end(berth):
    BerthLeaseFactory(berth=berth, start_date="2020-06-10", end_date="2020-09-14")

    with pytest.raises(ValidationError) as exception:
        BerthLeaseFactory(berth=berth, start_date="2020-01-01", end_date="2020-12-31")

    error_msg = str(exception.value)
    assert "Berth already has a lease" in error_msg


def test_berth_lease_non_overlapping_leases(berth):
    BerthLeaseFactory(berth=berth, start_date="2020-06-10", end_date="2020-09-14")
    BerthLeaseFactory(berth=berth, start_date="2020-01-01", end_date="2020-05-01")

    assert BerthLease.objects.count() == 2


@freeze_time("2020-06-01T08:00:00Z")
def test_allow_berth_lease_to_start_on_the_day_another_ends(berth):
    lease = BerthLeaseFactory(
        berth=berth, start_date="2020-01-01", end_date="2020-06-01"
    )
    assert not BerthLease.objects.get(id=lease.id).is_active

    BerthLeaseFactory(berth=berth, start_date="2020-06-01", end_date="2020-09-14")
    assert BerthLease.objects.count() == 2


@freeze_time("2020-01-01T08:00:00Z")
def test_winter_storage_lease_over_a_year_raise_error():
    with pytest.raises(ValidationError) as exception:
        WinterStorageLeaseFactory(start_date="2020-01-01", end_date="2022-01-21")

    error_msg = str(exception.value)
    assert "Lease cannot last for more than a year" in error_msg


@freeze_time("2020-01-01T08:00:00Z")
def test_winter_storage_lease_one_year_no_error():
    WinterStorageLeaseFactory(start_date="2020-01-01", end_date="2021-01-01")

    assert WinterStorageLease.objects.count() == 1
