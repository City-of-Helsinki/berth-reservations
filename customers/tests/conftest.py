import pytest

from .factories import BoatFactory


@pytest.fixture
def boat():
    boat = BoatFactory()
    return boat
