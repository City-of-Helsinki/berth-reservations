import pytest
from django.conf import settings
from django_ilmoitin.models import NotificationTemplate
from factory.random import randgen
from requests import RequestException

from applications.enums import ApplicationAreaType
from applications.tests.factories import (
    BerthApplicationFactory,
    WinterStorageApplicationFactory,
)
from berth_reservations.tests.conftest import *  # noqa
from customers.tests.factories import CustomerProfileFactory
from leases.tests.conftest import *  # noqa
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from resources.tests.conftest import *  # noqa
from resources.tests.factories import BerthTypeFactory

from ..providers import BamboraPayformProvider
from .factories import (
    AdditionalProductFactory,
    BerthProductFactory,
    OrderFactory,
    OrderLineFactory,
    OrderLogEntryFactory,
    WinterStorageProductFactory,
)
from .utils import random_price, random_tax

FAKE_BAMBORA_API_URL = "https://fake-bambora-api-url/api"
PROVIDER_BASE_CONFIG = {
    "VENE_PAYMENTS_BAMBORA_API_URL": "https://real-bambora-api-url/api",
    "VENE_PAYMENTS_BAMBORA_API_KEY": "dummy-key",
    "VENE_PAYMENTS_BAMBORA_API_SECRET": "dummy-secret",
    "VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS": ["dummy-bank"],
}


@pytest.fixture
def berth_price_group():
    # The BerthType (BT) save automatically creates a BerthPriceGroup (BPG) with the width
    # of the BT as name of the BPG. The BPG Factory assigns a random word as name, so, to avoid
    # hacky solutions, we instead create first the BT that are going to be assigned to the BPG
    # (all with the same width to have a single BPG) and then return the BPG associated to those BTs.
    width = randgen.uniform(1, 999)
    bt = BerthTypeFactory.create_batch(randgen.randint(1, 10), width=width)[0]

    berth_price_group = bt.price_group
    return berth_price_group


@pytest.fixture
def berth_product():
    berth_product = BerthProductFactory()
    return berth_product


@pytest.fixture
def winter_storage_product():
    winter_storage_product = WinterStorageProductFactory()
    return winter_storage_product


@pytest.fixture
def additional_product():
    additional_product = AdditionalProductFactory()
    return additional_product


def _generate_order(order_type: str = None):
    customer_profile = CustomerProfileFactory()
    if order_type == "berth_order":
        order = OrderFactory(
            customer=customer_profile,
            product=BerthProductFactory(),
            lease=BerthLeaseFactory(
                application=BerthApplicationFactory(), customer=customer_profile
            ),
        )
    elif order_type == "winter_storage_order":
        order = OrderFactory(
            customer=customer_profile,
            product=WinterStorageProductFactory(),
            lease=WinterStorageLeaseFactory(
                application=WinterStorageApplicationFactory(), customer=customer_profile
            ),
        )
    elif order_type == "unmarked_winter_storage_order":
        order = OrderFactory(
            customer=customer_profile,
            product=WinterStorageProductFactory(),
            lease=WinterStorageLeaseFactory(
                application=WinterStorageApplicationFactory(
                    area_type=ApplicationAreaType.UNMARKED
                ),
                customer=customer_profile,
            ),
        )
    elif order_type == "empty_order":
        order = OrderFactory(
            customer=customer_profile,
            price=random_price(),
            tax_percentage=random_tax(),
            product=None,
            lease=None,
        )
    else:
        order = OrderFactory(customer=customer_profile)
    return order


@pytest.fixture
def order(request):
    order_type = request.param if hasattr(request, "param") else None
    return _generate_order(order_type)


@pytest.fixture
def order_with_products(request):
    order_type = request.param if hasattr(request, "param") else None

    order = _generate_order(order_type)

    OrderLineFactory(order=order)
    OrderLineFactory(order=order)
    OrderLineFactory(order=order)
    OrderLineFactory(order=order)

    return order


@pytest.fixture
def berth_order(customer_profile):
    order = _generate_order("berth_order")
    return order


@pytest.fixture
def winter_storage_order(customer_profile):
    order = _generate_order("winter_storage_order")
    return order


@pytest.fixture
def order_line():
    order_line = OrderLineFactory()
    return order_line


@pytest.fixture
def order_log_entry():
    order_log_entry = OrderLogEntryFactory()
    return order_log_entry


@pytest.fixture()
def provider_base_config():
    return PROVIDER_BASE_CONFIG


@pytest.fixture()
def payment_provider(provider_base_config):
    """When it doesn't matter if request is contained within provider the fixture can still be used"""
    return BamboraPayformProvider(
        config=provider_base_config, ui_return_url=settings.VENE_UI_RETURN_URL
    )


def create_bambora_provider(provider_base_config, request):
    """Helper for creating a new instance of provider with request and optional return_url contained within"""
    return BamboraPayformProvider(
        config=provider_base_config,
        request=request,
        ui_return_url=settings.VENE_UI_RETURN_URL,
    )


def mocked_response_create(*args, **kwargs):
    """Mock Bambora auth token responses based on provider url"""

    class MockResponse:
        def __init__(self, data, status_code=200):
            self.json_data = data
            self.status_code = status_code

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code != 200:
                raise RequestException(
                    "Mock request error with status_code {}.".format(self.status_code)
                )
            pass

    if args[0].startswith(FAKE_BAMBORA_API_URL):
        return MockResponse(data={}, status_code=500)
    else:
        return MockResponse(
            data={"result": 0, "token": "token123", "type": "e-payment"}
        )


@pytest.fixture
def notification_template_orders_approved():
    from ..notifications import NotificationType

    for value in NotificationType.values:
        notification = NotificationTemplate.objects.language("fi").create(
            type=value,
            subject="test order approved subject, event: {{ order.order_number }}!",
            body_html="<b>{{ order.order_number }} {{ payment_url }}</b>",
            body_text="{{ order.order_number }} {{ payment_url }}",
        )
        notification.create_translation(
            "en",
            subject="test order approved subject, event: {{ order.order_number }}!",
            body_html="<b>{{ order.order_number }} {{ payment_url }}</b>",
            body_text="{{ order.order_number }} {{ payment_url }}",
        )
