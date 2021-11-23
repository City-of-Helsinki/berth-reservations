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
from customers.enums import OrganizationType
from customers.services import HelsinkiProfileUser
from customers.tests.factories import CustomerProfileFactory, OrganizationFactory
from customers.utils import get_customer_hash
from leases.tests.conftest import *  # noqa
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from resources.enums import AreaRegion
from resources.tests.conftest import *  # noqa
from resources.tests.factories import WinterStorageSectionFactory

from ..enums import (
    OrderStatus,
    OrderType,
    PeriodType,
    PriceUnits,
    ProductServiceType,
    TalpaProductType,
)
from ..providers import BamboraPayformProvider, TalpaEComProvider
from ..utils import price_as_fractional_int, resolve_area, resolve_product_talpa_ecom_id
from .factories import (
    AdditionalProductFactory,
    BerthProductFactory,
    BerthSwitchOfferFactory,
    OrderFactory,
    OrderLineFactory,
    OrderLogEntryFactory,
    PlainAdditionalProductFactory,
    TalpaProductAccountingFactory,
    WinterStorageProductFactory,
)
from .utils import random_price, random_tax

FAKE_BAMBORA_API_URL = "https://fake-bambora-api-url/api"
BAMBORA_PROVIDER_BASE_CONFIG = {
    "VENE_PAYMENTS_BAMBORA_API_URL": "https://real-bambora-api-url/api",
    "VENE_PAYMENTS_BAMBORA_API_KEY": "dummy-key",
    "VENE_PAYMENTS_BAMBORA_API_SECRET": "dummy-secret",
    "VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS": ["dummy-bank"],
}
FAKE_TALPA_ECOM_ORDER_API_URL = "https://fake-talpa-ecom-api-url/api"
TALPA_ECOM_PROVIDER_BASE_CONFIG = {
    "VENE_PAYMENTS_TALPA_ECOM_PAYMENT_API_URL": "https://real-talpa-api-url/api/v1/payment",
    "VENE_PAYMENTS_TALPA_ECOM_ORDER_API_URL": "https://real-talpa-api-url/api/v1/order",
    "VENE_PAYMENTS_TALPA_ECOM_CHECKOUT_URL": "https://real-talpa-checkout-url",
    "VENE_PAYMENTS_TALPA_ECOM_API_NAMESPACE": "venepaikat",
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
            lease=BerthLeaseFactory(
                application=BerthApplicationFactory(),
                customer=customer_profile,
            ),
        )
    elif order_type == "winter_storage_order":
        order = OrderFactory(
            customer=customer_profile,
            lease=WinterStorageLeaseFactory(
                application=WinterStorageApplicationFactory(), customer=customer_profile
            ),
        )
    elif order_type == "unmarked_winter_storage_order":
        order = OrderFactory(
            customer=customer_profile,
            lease=WinterStorageLeaseFactory(
                application=WinterStorageApplicationFactory(
                    area_type=ApplicationAreaType.UNMARKED
                ),
                place=None,
                section=WinterStorageSectionFactory(),
                customer=customer_profile,
            ),
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
            application=BerthApplicationFactory(),
            customer=customer_profile,
        )
        OrderFactory(
            order_type=OrderType.LEASE_ORDER,
            customer=customer_profile,
            lease=lease,
            status=OrderStatus.PAID,
        )
        order = OrderFactory(
            order_type=OrderType.ADDITIONAL_PRODUCT_ORDER,
            customer=customer_profile,
            price=0,
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
    elif order_type == "non_billable_customer_order":
        OrganizationFactory(
            customer=customer_profile, organization_type=OrganizationType.NON_BILLABLE
        )
        order = OrderFactory(customer=customer_profile, status=OrderStatus.OFFERED)
    else:  # Also covers the case of `order_type == "empty_order"`
        order = OrderFactory(
            customer=customer_profile,
            price=random_price(),
            tax_percentage=random_tax(),
            product=None,
            lease=None,
        )
    return order


@pytest.fixture
def order(request):
    order_type = request.param if hasattr(request, "param") else None
    return _generate_order(order_type)


@pytest.fixture
def order_with_products(request):
    order_type = request.param if hasattr(request, "param") else None

    order = _generate_order(order_type)

    OrderLineFactory(order=order, product__service=ProductServiceType.STORAGE_ON_ICE)
    OrderLineFactory(order=order, product__service=ProductServiceType.STORAGE_ON_ICE)
    OrderLineFactory(order=order, product__service=ProductServiceType.STORAGE_ON_ICE)
    OrderLineFactory(order=order, product__service=ProductServiceType.STORAGE_ON_ICE)

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
def non_billable_customer_order(customer_profile):
    order = _generate_order("non_billable_customer_order")
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
def bambora_provider_base_config():
    return BAMBORA_PROVIDER_BASE_CONFIG


@pytest.fixture()
def talpa_ecom_provider_base_config():
    return TALPA_ECOM_PROVIDER_BASE_CONFIG


@pytest.fixture
def berth_switch_offer():
    offer = BerthSwitchOfferFactory()
    return offer


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
def bambora_payment_provider(bambora_provider_base_config):
    """When it doesn't matter if request is contained within provider the fixture can still be used"""
    return BamboraPayformProvider(
        config=bambora_provider_base_config, ui_return_url=settings.VENE_UI_RETURN_URL
    )


@pytest.fixture()
def talpa_ecom_payment_provider(talpa_ecom_provider_base_config):
    """When it doesn't matter if request is contained within provider the fixture can still be used"""
    return TalpaEComProvider(config=talpa_ecom_provider_base_config)


def create_bambora_provider(bambora_provider_base_config, request):
    """Helper for creating a new instance of provider with request and optional return_url contained within"""
    return BamboraPayformProvider(
        config=bambora_provider_base_config,
        request=request,
        ui_return_url=settings.VENE_UI_RETURN_URL,
    )


def create_talpa_ecom_provider(talpa_ecom_provider_base_config, request):
    """Helper for creating a new instance of provider with a  specific request"""
    return TalpaEComProvider(
        config=talpa_ecom_provider_base_config,
        request=request,
    )


def mocked_bambora_response_create(*args, **kwargs):
    """Mock Bambora auth token responses based on provider url"""
    if args[0].startswith(FAKE_BAMBORA_API_URL):
        return MockResponse(data={}, status_code=500)
    else:
        return MockResponse(
            data={"result": 0, "token": "token123", "type": "e-payment"}
        )


def mocked_talpa_ecom_order_response(order):
    """Mock the Order object that Talpa returns"""
    return {
        "orderId": "aa48b642-72f9-4d9b-8e1f-161c8cfe9702",
        "namespace": "venepaikat",
        "user": get_customer_hash(order.customer),
        "createdAt": "2021-11-04T13:42:09.306265",
        "items": [
            {
                "orderItemId": "8c9bc852-bfbe-357b-961d-11b414fccd41",
                "orderId": "aa48b642-72f9-4d9b-8e1f-161c8cfe9702",
                "productId": resolve_product_talpa_ecom_id(
                    order.product, resolve_area(order)
                ),
                "productName": order.product.name,
                "unit": "pcs",
                "quantity": 1,
                "rowPriceNet": price_as_fractional_int(order.pretax_price),
                "rowPriceVat": price_as_fractional_int(order.price)
                - price_as_fractional_int(order.pretax_price),
                "rowPriceTotal": price_as_fractional_int(order.price),
                "vatPercentage": "24",
                "priceNet": price_as_fractional_int(order.pretax_price),
                "priceVat": price_as_fractional_int(order.price)
                - price_as_fractional_int(order.pretax_price),
                "priceTotal": price_as_fractional_int(order.price),
                "periodFrequency": None,
                "periodUnit": None,
                "periodCount": None,
                "startDate": None,
                "billingStartDate": None,
                "meta": [],
            }
        ],
        "customer": {
            "firstName": order.customer_first_name,
            "lastName": order.customer_first_name,
            "email": order.customer_email,
            "phone": order.customer_phone,
        },
        "status": "draft",
        "type": "order",
        "checkoutUrl": f"{TALPA_ECOM_PROVIDER_BASE_CONFIG['VENE_PAYMENTS_TALPA_ECOM_CHECKOUT_URL']}/"
        "aa48b642-72f9-4d9b-8e1f-161c8cfe9702",
        "priceNet": price_as_fractional_int(order.total_pretax_price),
        "priceVat": order.total_tax_percentage,
        "priceTotal": price_as_fractional_int(order.total_price),
    }


def mocked_response_talpa_ecom_order(order):
    """Mock the whole Order response that Talpa returns"""

    def wrapper(*args, **kwargs):
        if (
            args[0] and args[0].startswith(FAKE_TALPA_ECOM_ORDER_API_URL)
        ) or not hasattr(order, "product"):
            return MockResponse(data={}, status_code=500)
        else:
            return MockResponse(data=mocked_talpa_ecom_order_response(order))

    return wrapper


def mocked_response_talpa_ecom_errors(errors: dict = None, status_code: int = 400):
    """Mock the error response that Talpa returns, with optional custom error messages or status code"""

    def wrapper(*args, **kwargs):
        response_errors = {
            "errors": [
                {
                    "code": "request-validation-failed",
                    "message": "headers.user is a required field",
                }
                if errors is None
                else errors
            ]
        }
        return MockResponse(data=response_errors, status_code=status_code)

    return wrapper


def mocked_refund_response_create(*args, **kwargs):
    if any([arg.startswith(FAKE_BAMBORA_API_URL) for arg in args]):
        return MockResponse(data={"result": 10})
    else:
        return MockResponse(data={"result": 0, "refund_id": 123456, "type": "instant"})


def mocked_refund_payment_details(*args, products=None, **kwargs):
    def wrapper(*args, **kwargs):
        if any([arg.startswith(FAKE_BAMBORA_API_URL) for arg in args]):
            return MockResponse(data={"result": 10})
        else:
            from ..providers.bambora_payform import BamboraPaymentDetails

            customer = kwargs.get(
                "customer",
                {
                    "firstname": "Test",
                    "lastname": "Person",
                    "email": "test.person@email.com",
                    "address_street": "",
                    "address_city": "",
                    "address_zip": "",
                    "address_country": "",
                },
            )
            order_number = kwargs.get("order_number", "abc123")
            refunds = kwargs.get("refunds", [])
            payment_products = products or [
                {
                    "id": "as123",
                    "product_id": 1123,
                    "title": "Product 1",
                    "count": 1,
                    "pretax_price": 100,
                    "tax": 24,
                    "price": 124,
                    "type": 1,
                },
            ]
            amount = sum([int(product.get("price")) for product in payment_products])

            return BamboraPaymentDetails(
                {
                    "id": 123,
                    "amount": amount,
                    "currency": "EUR",
                    "order_number": order_number,
                    "created_at": "2018-09-12 08:30:22",
                    "status": 4,
                    "refund_type": "email",
                    "source": {"object": "card", "brand": "Visa"},
                    "customer": customer,
                    "payment_products": payment_products,
                    "refunds": refunds,
                }
            )

    return wrapper


@pytest.fixture()
def default_talpa_product_accounting():
    return [
        TalpaProductAccountingFactory(
            region=AreaRegion.EAST, product_type=TalpaProductType.BERTH
        ),
        TalpaProductAccountingFactory(
            region=AreaRegion.EAST, product_type=TalpaProductType.WINTER
        ),
        TalpaProductAccountingFactory(
            region=AreaRegion.WEST, product_type=TalpaProductType.BERTH
        ),
        TalpaProductAccountingFactory(
            region=AreaRegion.WEST, product_type=TalpaProductType.WINTER
        ),
    ]
