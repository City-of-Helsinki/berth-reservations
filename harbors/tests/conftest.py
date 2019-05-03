import pytest

from berth_reservations.tests.conftest import *  # noqa

from ..models import BoatType, Harbor, WinterStorageArea


@pytest.fixture
def boat_type():
    boat_type = BoatType.objects.language("en").create(name="Dinghy")
    boat_type.set_current_language("fi")
    boat_type.name = "Jollavene"
    boat_type.save()
    return boat_type


@pytest.fixture
def harbor():
    harbor = Harbor.objects.language("en").create(name="Sunny Harbor")
    harbor.set_current_language("fi")
    harbor.name = "Aurinkoinen satama"
    harbor.zip_code = "00100"
    harbor.save()
    return harbor


@pytest.fixture
def winter_area():
    winter_area = WinterStorageArea.objects.language("en").create(name="Snowy Area")
    winter_area.set_current_language("fi")
    winter_area.name = "Luminen alue"
    winter_area.zip_code = "00200"
    winter_area.save()
    return winter_area
