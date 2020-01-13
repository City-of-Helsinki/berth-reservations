import pytest

from berth_reservations.tests.conftest import *  # noqa
from customers.tests.factories import BoatFactory

from .factories import BerthLeaseFactory, WinterStorageLeaseFactory


@pytest.fixture
def berth_lease():
    boat = BoatFactory()
    return BerthLeaseFactory(customer=boat.owner, boat=boat)


@pytest.fixture
def winter_storage_lease():
    boat = BoatFactory()
    return WinterStorageLeaseFactory(customer=boat.owner, boat=boat)
