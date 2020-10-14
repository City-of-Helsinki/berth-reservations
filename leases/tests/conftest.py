import pytest

from applications.tests.conftest import *  # noqa
from berth_reservations.tests.conftest import *  # noqa
from customers.tests.conftest import *  # noqa
from customers.tests.factories import BoatFactory
from resources.tests.conftest import *  # noqa

from ..stickers import create_ws_sticker_sequences
from .factories import BerthLeaseFactory, WinterStorageLeaseFactory


@pytest.fixture
def sticker_sequences():
    create_ws_sticker_sequences()


@pytest.fixture
def berth_lease():
    boat = BoatFactory()
    return BerthLeaseFactory(customer=boat.owner, boat=boat)


@pytest.fixture
def winter_storage_lease():
    boat = BoatFactory()
    return WinterStorageLeaseFactory(customer=boat.owner, boat=boat)
