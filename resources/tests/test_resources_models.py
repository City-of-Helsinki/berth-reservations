import random

import pytest  # noqa
from freezegun import freeze_time

from leases.enums import LeaseStatus
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from leases.utils import (
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
    calculate_winter_storage_lease_end_date,
)

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
@pytest.mark.parametrize("renew_automatically", [True, False])
def test_berth_is_available_lease_status(
    superuser_api_client, berth, status, renew_automatically
):
    BerthLeaseFactory(
        berth=berth, renew_automatically=renew_automatically, status=LeaseStatus(status)
    )
    assert Berth.objects.get(id=berth.id).is_available


def test_berth_is_available_last_season_dont_renew_automatically(
    superuser_api_client, berth
):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    start_date = start_date.replace(year=start_date.year - 1)
    end_date = end_date.replace(year=end_date.year - 1)

    BerthLeaseFactory(
        berth=berth, start_date=start_date, end_date=end_date, renew_automatically=False
    )
    assert Berth.objects.get(id=berth.id).is_available


@pytest.mark.parametrize("status", ["drafted", "offered", "expired", "refused"])
def test_berth_is_available_last_season_renew_automatically_invalid_status(
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
        renew_automatically=False,
        status=LeaseStatus(status),
    )
    assert Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize("status", ["drafted", "offered", "paid", "expired", "refused"])
@pytest.mark.parametrize("renew_automatically", [True, False])
def test_berth_is_available_ends_during_season(
    superuser_api_client, berth, status, renew_automatically
):
    end_date = calculate_berth_lease_end_date()
    end_date = end_date.replace(month=end_date.month - 1)

    BerthLeaseFactory(
        berth=berth,
        end_date=end_date,
        renew_automatically=renew_automatically,
        status=LeaseStatus(status),
    )
    assert Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize("status", ["drafted", "offered", "paid"])
@pytest.mark.parametrize("renew_automatically", [True, False])
def test_berth_is_not_available_valid_through_whole_season(
    superuser_api_client, berth, status, renew_automatically
):
    BerthLeaseFactory(
        berth=berth, status=status, renew_automatically=renew_automatically
    )
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
        renew_automatically=True,
    )
    assert not Berth.objects.get(id=berth.id).is_available


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
@pytest.mark.parametrize("status", ["drafted", "offered", "paid", "expired", "refused"])
def test_winter_storage_place_is_available_ends_during_season(
    superuser_api_client, winter_storage_place, status
):
    end_date = calculate_winter_storage_lease_end_date()
    end_date = end_date.replace(month=end_date.month - 1)

    WinterStorageLeaseFactory(
        place=winter_storage_place, end_date=end_date, status=LeaseStatus(status),
    )
    assert WinterStoragePlace.objects.get(id=winter_storage_place.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize("status", ["drafted", "offered", "paid"])
def test_winter_storage_place_is_not_available_valid_through_whole_season(
    superuser_api_client, winter_storage_place, status
):
    WinterStorageLeaseFactory(place=winter_storage_place, status=status)
    assert not WinterStoragePlace.objects.get(id=winter_storage_place.id).is_available


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
