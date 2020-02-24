import pytest

from berth_reservations.tests.conftest import *  # noqa

from .factories import BoatFactory


@pytest.fixture
def boat():
    boat = BoatFactory()
    return boat
