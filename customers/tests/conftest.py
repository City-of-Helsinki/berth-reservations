import pytest

from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.factories import CustomerProfileFactory
from berth_reservations.tests.utils import MockResponse
from customers.schema import ProfileNode
from resources.tests.conftest import berth, boat_type  # noqa
from users.tests.conftest import user  # noqa
from utils.relay import to_global_id

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


def mocked_response_profile(count=3, data=None, use_edges=True, *args, **kwargs):
    def wrapper(*args, **kwargs):
        profiles = []
        for _i in range(0, count):
            profile = CustomerProfileFactory()
            profiles.append(
                {
                    "id": to_global_id(ProfileNode, profile.id),
                    "first_name": profile.user.first_name,
                    "last_name": profile.user.last_name,
                    "primary_email": {"email": profile.user.email},
                }
            )
        if data:
            profiles.append(data)

        if use_edges:
            edges = [{"node": node} for node in profiles]
            return MockResponse(
                data={
                    "data": {
                        "profiles": {"edges": edges},
                        "pageInfo": {"endCursor": "", "hasNextPage": False},
                    }
                }
            )

        profiles = {"profile": profiles[0]}
        return MockResponse(data={"data": profiles})

    return wrapper
