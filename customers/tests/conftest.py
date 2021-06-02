import pytest
from django_ilmoitin.models import NotificationTemplate
from faker import Faker
from rest_framework.test import APIClient

from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.factories import CustomerProfileFactory
from berth_reservations.tests.utils import MockResponse
from customers.schema import ProfileNode
from payments.notifications import NotificationType
from resources.tests.conftest import berth, boat_type  # noqa
from users.tests.conftest import user  # noqa
from utils.relay import to_global_id

from .factories import BoatCertificateFactory, BoatFactory, OrganizationFactory

MOCK_HKI_PROFILE_ADDRESS: dict = {
    "address": "Street 1",
    "postal_code": "00100",
    "city": "Helsinki",
}


@pytest.fixture
def rest_api_client():
    return APIClient()


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


@pytest.fixture
def hki_profile_address() -> dict:
    return MOCK_HKI_PROFILE_ADDRESS


def get_customer_profile_dict() -> dict:
    faker = Faker()
    profile = CustomerProfileFactory()
    return {
        "id": to_global_id(ProfileNode, profile.id),
        "first_name": profile.user.first_name,
        "last_name": profile.user.last_name,
        "primary_email": {"email": profile.user.email},
        "primary_phone": {"phone": faker.phone_number()},
        "primary_address": MOCK_HKI_PROFILE_ADDRESS,
    }


def mocked_response_profile(count=3, data=None, use_edges=True, *args, **kwargs):
    def wrapper(*args, **kwargs):
        profiles = []

        for _i in range(0, count):
            profiles.append(get_customer_profile_dict())
        if data:
            if isinstance(data, dict):
                profiles.append(data)
            else:
                profiles.extend(data)

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


def mocked_response_my_profile(data="", *args, **kwargs):
    def wrapper(*args, **kwargs):
        if data != "":
            profile_dict = data
        else:
            profile_dict = get_customer_profile_dict()
        my_profile = {"my_profile": profile_dict}
        return MockResponse(data={"data": my_profile})

    return wrapper


@pytest.fixture
def notification_template_sms_invoice_notice():
    return NotificationTemplate.objects.language("fi").create(
        type=NotificationType.SMS_INVOICE_NOTICE.value,
        subject="SMS invoice notice",
        body_html="Remember to pay your invoice {{ product_name }} by {{ due_date }}",
        body_text="Remember to pay your invoice {{ product_name }} by {{ due_date }}",
    )
