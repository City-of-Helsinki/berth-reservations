import pytest

from berth_reservations.tests.conftest import *  # noqa

from .factories import BoatCertificateFactory, BoatFactory


@pytest.fixture
def boat():
    boat = BoatFactory()
    return boat


@pytest.fixture
def boat_certificate():
    boat_certificate = BoatCertificateFactory()
    return boat_certificate
