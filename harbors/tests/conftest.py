import pytest

from berth_reservations.tests.conftest import *  # noqa

from .factories import BoatTypeFactory, HarborFactory, WinterStorageAreaFactory


@pytest.fixture
def boat_type():
    boat_type = BoatTypeFactory()
    boat_type.create_translation("fi", name="Jollavene")
    return boat_type


@pytest.fixture
def harbor():
    harbor = HarborFactory()
    harbor.create_translation("fi", name="Testisatama")
    return harbor


@pytest.fixture
def winter_area():
    winter_area = WinterStorageAreaFactory()
    winter_area.create_translation("fi", name="Testitalvisäilytysalue")
    return winter_area
