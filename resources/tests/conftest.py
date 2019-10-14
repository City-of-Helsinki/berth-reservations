import pytest

from berth_reservations.tests.conftest import *  # noqa

from .factories import (
    BerthFactory,
    BoatTypeFactory,
    HarborFactory,
    PierFactory,
    WinterStorageAreaFactory,
    WinterStoragePlaceFactory,
    WinterStorageSectionFactory,
)


@pytest.fixture
def boat_type():
    boat_type = BoatTypeFactory()
    return boat_type


@pytest.fixture
def harbor():
    harbor = HarborFactory()
    return harbor


@pytest.fixture
def pier():
    pier = PierFactory(suitable_boat_types__count=2)
    return pier


@pytest.fixture
def berth():
    berth = BerthFactory()
    return berth


@pytest.fixture
def winter_storage_area():
    winter_storage_area = WinterStorageAreaFactory()
    return winter_storage_area


@pytest.fixture
def winter_storage_section():
    winter_storage_section = WinterStorageSectionFactory()
    return winter_storage_section


@pytest.fixture
def winter_storage_place():
    winter_storage_place = WinterStoragePlaceFactory()
    return winter_storage_place
