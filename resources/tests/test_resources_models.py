import random
from datetime import date
from unittest import mock

import pytest  # noqa
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from freezegun import freeze_time

from leases.consts import ACTIVE_LEASE_STATUSES, INACTIVE_LEASE_STATUSES
from leases.enums import LeaseStatus
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from leases.utils import (
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
    calculate_winter_season_end_date,
    calculate_winter_season_start_date,
    calculate_winter_storage_lease_end_date,
    calculate_winter_storage_lease_start_date,
)
from payments.enums import OfferStatus
from payments.tests.factories import BerthSwitchOfferFactory

from ..models import Berth, Pier, WinterStoragePlace, WinterStorageSection
from .factories import (
    BerthFactory,
    PierFactory,
    WinterStoragePlaceFactory,
    WinterStorageSectionFactory,
)


def test_berth_is_available_no_leases(superuser_api_client, berth):
    assert Berth.objects.get(id=berth.id).is_available


@pytest.mark.parametrize("status", ["expired", "refused"])
def test_berth_is_available_lease_status(superuser_api_client, berth, status):
    BerthLeaseFactory(berth=berth, status=LeaseStatus(status))
    assert Berth.objects.get(id=berth.id).is_available


@pytest.mark.parametrize("status", ["drafted", "offered", "expired", "refused"])
def test_berth_is_available_last_season_invalid_status(
    superuser_api_client, berth, status
):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    start_date = start_date.replace(year=start_date.year - 1)
    end_date = end_date.replace(year=end_date.year - 1)

    BerthLeaseFactory(
        berth=berth,
        start_date=start_date,
        end_date=end_date,
        status=LeaseStatus(status),
    )
    assert Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01")
@pytest.mark.parametrize("status", ["drafted", "offered", "paid", "error"])
def test_berth_is_not_available_ends_during_season_before_lease_ends(
    superuser_api_client, berth, status
):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date() - relativedelta(month=6, day=29)

    BerthLeaseFactory(
        berth=berth,
        start_date=start_date,
        end_date=end_date,
        status=LeaseStatus(status),
    )
    with mock.patch(
        "leases.utils.calculate_berth_lease_start_date"
    ) as mock_start, mock.patch(
        "leases.utils.calculate_berth_lease_end_date"
    ) as mock_end:
        mock_start.return_value = date(2020, 6, 10)
        mock_end.return_value = date(2020, 9, 15)
        assert not Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01")
def test_berth_is_available_ends_during_season_after_lease_ends(
    superuser_api_client, berth
):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date() - relativedelta(month=6, day=29)

    BerthLeaseFactory(
        berth=berth,
        start_date=start_date,
        end_date=end_date,
        # The lease is terminated at some point and set to end on end_date
        status=LeaseStatus.TERMINATED,
    )
    with mock.patch(
        "resources.models.calculate_season_start_date"
    ) as mock_start, mock.patch(
        "resources.models.calculate_berth_lease_end_date"
    ) as mock_end:
        mock_start.return_value = date(2020, 6, 30)
        mock_end.return_value = date(2020, 9, 15)
        assert Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize("status", ["drafted", "offered", "paid"])
def test_berth_is_not_available_valid_through_whole_season(
    superuser_api_client, berth, status
):
    BerthLeaseFactory(berth=berth, status=status)
    assert not Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
def test_berth_is_not_available_auto_renew_last_season(superuser_api_client, berth):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    start_date = start_date.replace(year=start_date.year - 1)
    end_date = end_date.replace(year=end_date.year - 1)
    BerthLeaseFactory(
        berth=berth,
        start_date=start_date,
        end_date=end_date,
        status=LeaseStatus.PAID,
    )
    assert not Berth.objects.get(id=berth.id).is_available


@pytest.mark.parametrize(
    "date", ["2020-01-01T08:00:00Z", "2020-06-30T08:00:00Z", "2020-11-01T08:00:00Z"]
)
@pytest.mark.parametrize("status", ACTIVE_LEASE_STATUSES)
def test_berth_is_not_available_next_season(status, date):
    with freeze_time(date):
        lease = BerthLeaseFactory(status=status)

        # Need to fetch the berth from the DB to get the annotated value
        assert not Berth.objects.get(id=lease.berth_id).is_available


@pytest.mark.parametrize(
    "freeze_date,expected_is_available",
    [
        ("2018-09-14T08:00:00Z", True),
        ("2019-09-14T08:00:00Z", True),
        ("2019-09-15T08:00:00Z", True),
        ("2020-01-01T08:00:00Z", True),
        ("2020-06-09T08:00:00Z", True),
        ("2020-06-10T08:00:00Z", True),
        ("2020-06-11T08:00:00Z", True),
        ("2020-06-12T08:00:00Z", True),
        ("2020-09-12T08:00:00Z", True),
        ("2020-09-13T08:00:00Z", True),
        ("2020-09-14T08:00:00Z", False),
        ("2020-09-15T08:00:00Z", False),
        ("2020-09-16T08:00:00Z", False),
        ("2021-01-01T08:00:00Z", False),
        ("2021-06-09T08:00:00Z", False),
        ("2021-06-10T08:00:00Z", False),
        ("2021-06-11T08:00:00Z", False),
        ("2021-06-12T08:00:00Z", False),
        ("2021-07-12T08:00:00Z", False),
        ("2021-09-14T08:00:00Z", False),
        ("2021-09-15T08:00:00Z", False),
        ("2021-12-31T08:00:00Z", False),
        ("2022-01-01T08:00:00Z", False),
        ("2022-06-09T08:00:00Z", False),
        ("2022-06-10T08:00:00Z", False),
        ("2022-06-11T08:00:00Z", False),
        ("2022-06-12T08:00:00Z", False),
        ("2022-09-13T08:00:00Z", False),
        ("2022-09-14T08:00:00Z", True),
        ("2022-09-15T08:00:00Z", True),
        ("2022-09-16T08:00:00Z", True),
        ("2023-06-09T08:00:00Z", True),
        ("2023-06-10T08:00:00Z", True),
        ("2023-06-11T08:00:00Z", True),
        ("2024-06-11T08:00:00Z", True),
    ],
)
def test_berth_is_available_one_paid_lease(freeze_date, expected_is_available):
    with freeze_time(freeze_date):
        lease = BerthLeaseFactory(
            status=LeaseStatus.PAID,
            start_date=date(2021, 6, 10),
            end_date=date(2021, 9, 14),
        )

        # Need to fetch the berth from the DB to get the annotated value
        assert (
            Berth.objects.get(id=lease.berth_id).is_available == expected_is_available
        )


@pytest.mark.parametrize(
    "date", ["2020-01-01T08:00:00Z", "2020-06-30T08:00:00Z", "2020-11-01T08:00:00Z"]
)
@pytest.mark.parametrize("status", INACTIVE_LEASE_STATUSES)
def test_berth_is_available_next_season(date, status):
    with freeze_time(date):
        lease = BerthLeaseFactory(status=status)

        # Need to fetch the berth from the DB to get the annotated value
        assert Berth.objects.get(id=lease.berth_id).is_available


@pytest.mark.parametrize(
    "date", ["2020-01-01T08:00:00Z", "2020-06-30T08:00:00Z", "2020-11-01T08:00:00Z"]
)
@pytest.mark.parametrize("inactive_status", INACTIVE_LEASE_STATUSES)
def test_berth_is_available_rejected_new_lease(date, inactive_status):
    with freeze_time(date):
        old_lease = BerthLeaseFactory(
            status=LeaseStatus.PAID,
            start_date=calculate_berth_lease_start_date() - relativedelta(years=1),
            end_date=calculate_berth_lease_end_date() - relativedelta(years=1),
        )
        BerthLeaseFactory(
            status=inactive_status, berth=old_lease.berth, customer=old_lease.customer
        )

        # Need to fetch the berth from the DB to get the annotated value
        assert Berth.objects.get(id=old_lease.berth_id).is_available


@pytest.mark.parametrize(
    "date", ["2020-01-01T08:00:00Z", "2020-06-30T08:00:00Z", "2020-11-01T08:00:00Z"]
)
def test_berth_is_not_available_renew_pending(date):
    with freeze_time(date):
        lease = BerthLeaseFactory(
            status=LeaseStatus.PAID,
            start_date=calculate_berth_lease_start_date() - relativedelta(years=1),
            end_date=calculate_berth_lease_end_date() - relativedelta(years=1),
        )

        # Need to fetch the berth from the DB to get the annotated value
        assert not Berth.objects.get(id=lease.berth_id).is_available


@pytest.mark.parametrize(
    "status",
    [
        OfferStatus.ACCEPTED,
        OfferStatus.REJECTED,
        OfferStatus.EXPIRED,
        OfferStatus.CANCELLED,
    ],
)
def test_berth_is_available_inactive_offer(status):
    offer = BerthSwitchOfferFactory(
        status=status, due_date=today() + relativedelta(days=14)
    )

    assert Berth.objects.get(id=offer.berth_id).is_available


@pytest.mark.parametrize("status", [OfferStatus.DRAFTED, OfferStatus.OFFERED])
def test_berth_is_not_available_active_offer(status):
    offer = BerthSwitchOfferFactory(
        status=status, due_date=today() + relativedelta(days=14)
    )

    assert not Berth.objects.get(id=offer.berth_id).is_available


def test_pier_number_of_places():
    pier = PierFactory()
    free_berths = random.randint(1, 10)
    inactive_berths = random.randint(1, 10)

    for number in range(0, free_berths):
        BerthFactory(pier=pier, number=number, is_active=True)

    for number in range(free_berths, free_berths + inactive_berths):
        BerthFactory(pier=pier, number=number, is_active=False)

    pier = Pier.objects.get(pk=pier.pk)
    assert pier.number_of_free_places == free_berths
    assert pier.number_of_inactive_places == inactive_berths
    assert pier.number_of_places == free_berths + inactive_berths


def test_winter_storage_place_is_available_no_leases(
    superuser_api_client, winter_storage_place
):
    assert WinterStoragePlace.objects.get(id=winter_storage_place.id).is_available


@pytest.mark.parametrize("status", ["expired", "refused"])
def test_winter_storage_place_is_available_lease_status(
    superuser_api_client, winter_storage_place, status
):
    WinterStorageLeaseFactory(place=winter_storage_place, status=LeaseStatus(status))
    assert WinterStoragePlace.objects.get(id=winter_storage_place.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize(
    "status", ["drafted", "offered", "terminated", "expired", "refused"]
)
def test_winter_storage_place_is_available_ends_during_season_after_lease_ends(
    superuser_api_client, winter_storage_place, status
):
    end_date = calculate_winter_storage_lease_end_date()
    end_date = end_date.replace(month=end_date.month - 1)

    WinterStorageLeaseFactory(
        place=winter_storage_place,
        end_date=end_date,
        status=LeaseStatus(status),
    )

    with mock.patch(
        "resources.models.calculate_winter_season_start_date"
    ) as mock_start, mock.patch(
        "resources.models.calculate_winter_storage_lease_end_date"
    ) as mock_end:
        mock_start.return_value = date(2020, 9, 15)
        mock_end.return_value = date(2021, 6, 10)

        assert WinterStoragePlace.objects.get(id=winter_storage_place.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize("status", ["drafted", "offered", "paid"])
def test_winter_storage_place_is_not_available_valid_through_whole_season(
    superuser_api_client, winter_storage_place, status
):
    WinterStorageLeaseFactory(place=winter_storage_place, status=status)
    assert not WinterStoragePlace.objects.get(id=winter_storage_place.id).is_available


@pytest.mark.parametrize(
    "date", ["2020-01-01T08:00:00Z", "2020-06-30T08:00:00Z", "2020-11-01T08:00:00Z"]
)
@pytest.mark.parametrize("status", ACTIVE_LEASE_STATUSES)
def test_winter_storage_place_is_not_available_next_season(status, date):
    with freeze_time(date):
        lease = WinterStorageLeaseFactory(status=status)

        # Need to fetch the berth from the DB to get the annotated value
        assert not WinterStoragePlace.objects.get(id=lease.place_id).is_available


@pytest.mark.parametrize(
    "date", ["2020-01-01T08:00:00Z", "2020-06-30T08:00:00Z", "2020-11-01T08:00:00Z"]
)
@pytest.mark.parametrize("status", INACTIVE_LEASE_STATUSES)
def test_winter_storage_place_is_available_next_season(date, status):
    with freeze_time(date):
        lease = WinterStorageLeaseFactory(status=status)

        # Need to fetch the berth from the DB to get the annotated value
        assert WinterStoragePlace.objects.get(id=lease.place_id).is_available


@pytest.mark.parametrize(
    "date", ["2020-01-01T08:00:00Z", "2020-06-30T08:00:00Z", "2020-11-01T08:00:00Z"]
)
@pytest.mark.parametrize("inactive_status", INACTIVE_LEASE_STATUSES)
def test_winter_storage_place_is_available_rejected_new_lease(date, inactive_status):
    with freeze_time(date):
        old_lease = WinterStorageLeaseFactory(
            status=LeaseStatus.PAID,
            start_date=calculate_winter_storage_lease_start_date()
            - relativedelta(years=1),
            end_date=calculate_winter_storage_lease_end_date() - relativedelta(years=1),
        )
        WinterStorageLeaseFactory(
            status=inactive_status, place=old_lease.place, customer=old_lease.customer
        )

        # Need to fetch the berth from the DB to get the annotated value
        assert WinterStoragePlace.objects.get(id=old_lease.place_id).is_available


@pytest.mark.parametrize(
    "date", ["2020-01-01T08:00:00Z", "2020-06-30T08:00:00Z", "2020-11-01T08:00:00Z"]
)
def test_winter_storage_place_is_not_available_renew_pending(date):
    with freeze_time(date):
        lease = WinterStorageLeaseFactory(
            status=LeaseStatus.PAID,
            start_date=calculate_winter_storage_lease_start_date()
            - relativedelta(years=1),
            end_date=calculate_winter_storage_lease_end_date() - relativedelta(years=1),
        )

        # Need to fetch the berth from the DB to get the annotated value
        assert not WinterStoragePlace.objects.get(id=lease.place_id).is_available


@freeze_time("2020-01-01T08:00:00Z")
def test_winter_storage_place_is_available_when_customer_terminates_lease(
    superuser_api_client, winter_storage_place, customer_profile
):
    season_start = calculate_winter_season_start_date()
    season_end = calculate_winter_season_end_date()

    # Terminated current season lease
    WinterStorageLeaseFactory(
        start_date=season_start,
        end_date=season_end,
        place=winter_storage_place,
        customer=customer_profile,
        status=LeaseStatus.TERMINATED,
    )
    # Paid previous season lease
    WinterStorageLeaseFactory(
        start_date=season_start - relativedelta(years=1),
        end_date=season_end - relativedelta(years=1),
        place=winter_storage_place,
        customer=customer_profile,
        status=LeaseStatus.PAID,
    )

    assert WinterStoragePlace.objects.get(id=winter_storage_place.id).is_available


def test_winter_storage_section_number_of_places():
    section = WinterStorageSectionFactory()
    free_places = random.randint(1, 10)
    inactive_places = random.randint(1, 10)

    for number in range(0, free_places):
        WinterStoragePlaceFactory(
            winter_storage_section=section, number=number, is_active=True
        )

    for number in range(free_places, free_places + inactive_places):
        WinterStoragePlaceFactory(
            winter_storage_section=section, number=number, is_active=False
        )

    section = WinterStorageSection.objects.get(pk=section.pk)
    assert section.number_of_free_places == free_places
    assert section.number_of_inactive_places == inactive_places
    assert section.number_of_places == free_places + inactive_places
