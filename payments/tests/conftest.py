from decimal import Decimal
from uuid import UUID

import pytest
from django.conf import settings

from applications.enums import ApplicationAreaType
from applications.tests.factories import (
    BerthApplicationFactory,
    WinterStorageApplicationFactory,
)
from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.utils import MockResponse
from customers.services import HelsinkiProfileUser
from customers.tests.factories import CustomerProfileFactory
from leases.tests.conftest import *  # noqa
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from resources.tests.conftest import *  # noqa

from ..enums import OrderStatus, OrderType, PeriodType, PriceUnits, ProductServiceType
from ..providers import BamboraPayformProvider
from .factories import (
    AdditionalProductFactory,
    BerthProductFactory,
    OrderFactory,
    OrderLineFactory,
    OrderLogEntryFactory,
    PlainAdditionalProductFactory,
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
    elif order_type == "additional_product_order":
        order = OrderFactory(
            order_type=OrderType.ADDITIONAL_PRODUCT_ORDER,
            customer=customer_profile,
            price=random_price(),
            tax_percentage=random_tax(),
            product=None,
            lease=BerthLeaseFactory(
                application=BerthApplicationFactory(), customer=customer_profile
            ),
        )
    elif order_type == "additional_product_order_with_lease_order":
        lease = BerthLeaseFactory(
            application=BerthApplicationFactory(), customer=customer_profile
        )
        OrderFactory(
            order_type=OrderType.LEASE_ORDER,
            customer=customer_profile,
            price=random_price(),
            tax_percentage=random_tax(),
            product=BerthProductFactory(),
            lease=lease,
            status=OrderStatus.PAID,
        )
        order = OrderFactory(
            order_type=OrderType.ADDITIONAL_PRODUCT_ORDER,
            customer=customer_profile,
            price=random_price(),
            tax_percentage=random_tax(),
            product=None,
            lease=lease,
        )
        storage_on_ice = PlainAdditionalProductFactory(
            service=ProductServiceType.STORAGE_ON_ICE,
            period=PeriodType.SEASON,
            tax_percentage=Decimal("24.00"),
            price_value=Decimal("60.00"),
            price_unit=PriceUnits.PERCENTAGE,
        )
        OrderLineFactory(order=order, product=storage_on_ice, price=Decimal("15.00"))
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
def helsinki_profile_user():
    return HelsinkiProfileUser(
        id=UUID("28319ebc-5eaf-4285-a565-15848225614b"),
        first_name="Matti",
        last_name="Virtanen",
        email="foo@bar.com",
        address="Street 1",
        postal_code="00100",
        city="Helsinki",
    )


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
    if args[0].startswith(FAKE_BAMBORA_API_URL):
        return MockResponse(data={}, status_code=500)
    else:
        return MockResponse(
            data={"result": 0, "token": "token123", "type": "e-payment"}
        )
