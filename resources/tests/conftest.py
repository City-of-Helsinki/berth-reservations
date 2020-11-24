import pytest

from applications.tests.conftest import berth_application  # noqa
from berth_reservations.tests.conftest import *  # noqa

from .factories import (
    AvailabilityLevelFactory,
    BerthFactory,
    BerthTypeFactory,
    BoatTypeFactory,
    HarborFactory,
    PierFactory,
    WinterStorageAreaFactory,
    WinterStoragePlaceFactory,
    WinterStoragePlaceTypeFactory,
    WinterStorageSectionFactory,
)


@pytest.fixture
def availability_level():
    availability_level = AvailabilityLevelFactory()
    return availability_level


@pytest.fixture
def boat_type():
    boat_type = BoatTypeFactory()
    boat_type.create_translation("fi", name="Jollavene")
    return boat_type


@pytest.fixture
def berth_type():
    berth_type = BerthTypeFactory()
    return berth_type


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


@pytest.fixture
def winter_storage_place_type():
    winter_storage_place_type = WinterStoragePlaceTypeFactory()
    return winter_storage_place_type
