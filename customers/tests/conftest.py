import pytest

from berth_reservations.tests.conftest import *  # noqa
from resources.tests.conftest import boat_type  # noqa

from .factories import BoatCertificateFactory, BoatFactory, OrganizationFactory


@pytest.fixture
def boat():
    boat = BoatFactory()
    return boat


@pytest.fixture
def boat_certificate():
    boat_certificate = BoatCertificateFactory()
    return boat_certificate


@pytest.fixture
def organization():
    organization = OrganizationFactory()
    return organization
