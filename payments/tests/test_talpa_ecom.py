from decimal import Decimal
from unittest import mock
from uuid import uuid4

import pytest
from django.http import HttpResponse

from applications.enums import ApplicationStatus
from berth_reservations.tests.utils import MockResponse
from customers.utils import get_customer_hash
from leases.enums import LeaseStatus
from payments.consts import (
    TALPA_ECOM_WEBHOOK_EVENT_ORDER_CANCELLED,
    TALPA_ECOM_WEBHOOK_EVENT_PAYMENT_PAID,
    TALPA_ECOM_WEBHOOK_EVENT_TYPES,
)
from payments.enums import OrderStatus
from payments.exceptions import (
    MissingOrderIDError,
    RequestValidationFailedError,
    ServiceUnavailableError,
)
from payments.models import Order, TalpaProductAccounting
from payments.providers import TalpaEComProvider
from payments.providers.talpa_ecom import TalpaEComPaymentDetails
from payments.tests.conftest import (
    create_talpa_ecom_provider,
    FAKE_TALPA_ECOM_ORDER_API_URL,
    mocked_response_talpa_ecom_errors,
    mocked_response_talpa_ecom_order,
    mocked_talpa_ecom_order_response,
)
from payments.utils import (
    resolve_area,
    resolve_order_place,
    resolve_product_talpa_ecom_id,
)
from resources.enums import BerthMooringType
from resources.models import Berth, WinterStorageSection
from utils.numbers import rounded


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_payment_success(
    talpa_ecom_payment_provider: TalpaEComProvider,
    order: Order,
    default_talpa_product_accounting: list[TalpaProductAccounting],
    rf,
):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    with mock.patch(
        "payments.providers.talpa_ecom.requests.post",
        side_effect=mocked_response_talpa_ecom_order(order),
    ):
        url = talpa_ecom_payment_provider.initiate_payment(order)
        assert (
            url
            == f"{talpa_ecom_payment_provider.config.get('VENE_PAYMENTS_TALPA_ECOM_CHECKOUT_URL')}/"
            f"aa48b642-72f9-4d9b-8e1f-161c8cfe9702"
            f"?user={get_customer_hash(order.customer)}"
        )


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_payment_validation_errors(
    talpa_ecom_payment_provider: TalpaEComProvider,
    order: Order,
    default_talpa_product_accounting: list[TalpaProductAccounting],
    rf,
):
    """Test the request creator raises service unavailable if request doesn't go through"""

    with mock.patch(
        "payments.providers.talpa_ecom.requests.post",
        side_effect=mocked_response_talpa_ecom_errors(
            errors={
                "code": "request-validation-failed",
                "message": "error message",
            }
        ),
    ):
        with pytest.raises(RequestValidationFailedError) as exception:
            talpa_ecom_payment_provider.initiate_payment(order)

        error_msg = str(exception.value)
        assert "error message" == error_msg


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_payment_error_unavailable(
    talpa_ecom_provider_base_config: dict,
    order: Order,
    default_talpa_product_accounting: list[TalpaProductAccounting],
    rf,
):
    """Test the request creator raises service unavailable if request doesn't go through"""

    invalid_config = {
        **talpa_ecom_provider_base_config,
        "VENE_PAYMENTS_TALPA_ECOM_ORDER_API_URL": FAKE_TALPA_ECOM_ORDER_API_URL,
    }
    unavailable_payment_provider = create_talpa_ecom_provider(
        invalid_config, rf.request()
    )

    with mock.patch(
        "payments.providers.talpa_ecom.requests.post",
        side_effect=mocked_response_talpa_ecom_order(order),
    ):
        with pytest.raises(ServiceUnavailableError):
            unavailable_payment_provider.initiate_payment(order)


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_handle_initiate_payment_success(
    talpa_ecom_payment_provider: TalpaEComProvider,
    order: Order,
    default_talpa_product_accounting: list[TalpaProductAccounting],
):
    """Test the response handler recognizes success and adds token as part of the returned url"""
    r = mocked_talpa_ecom_order_response(order)
    return_value = talpa_ecom_payment_provider.handle_initiate_payment(order, r)

    assert (
        return_value
        == f"{talpa_ecom_payment_provider.config.get('VENE_PAYMENTS_TALPA_ECOM_CHECKOUT_URL')}/"
        f"aa48b642-72f9-4d9b-8e1f-161c8cfe9702"
        f"?user={get_customer_hash(order.customer)}"
    )


def test_handle_initiate_payment_error_validation(
    talpa_ecom_payment_provider: TalpaEComProvider, order: Order
):
    """Test the response handler raises PayloadValidationError as expected"""
    r = {
        "errors": [
            {
                "code": "request-validation-failed",
                "message": "body.namespace is a required field\nbody.user is a required field",
            }
        ]
    }
    with pytest.raises(RequestValidationFailedError) as exception:
        talpa_ecom_payment_provider.handle_initiate_payment(order, r)

    assert "body.namespace is a required field\nbody.user is a required field" in str(
        exception.value
    )


def test_handle_initiate_payment_error_missing_id(
    talpa_ecom_payment_provider: TalpaEComProvider,
    order: Order,
):
    """Test the response handler raises PayloadValidationError as expected"""
    r = {}

    with pytest.raises(MissingOrderIDError) as exception:
        talpa_ecom_payment_provider.handle_initiate_payment(order, r)

    assert str(exception.value) == "Order did not contain an id"


@pytest.mark.parametrize(
    "order_with_products",
    ["berth_order", "winter_storage_order", "unmarked_winter_storage_order"],
    indirect=True,
)
def test_payload_add_products_success(
    talpa_ecom_payment_provider: TalpaEComProvider,
    order_with_products: Order,
    default_talpa_product_accounting: list[TalpaProductAccounting],
):
    """Test the products and total order price data is added correctly into payload"""
    payload = {}
    talpa_ecom_payment_provider.payload_add_products(
        payload,
        order_with_products,
        order_with_products.lease.application.language,
    )

    assert payload["priceNet"] == rounded(
        order_with_products.total_pretax_price, as_string=True
    )
    assert payload["priceTotal"] == rounded(
        order_with_products.total_price, as_string=True
    )
    assert payload["priceVat"] == str(
        rounded(order_with_products.total_price)
        - rounded(order_with_products.total_pretax_price)
    )

    assert "items" in payload
    products = payload.get("items")
    assert len(products) == 5  # 1 place product + 4 additional products
    # As there's no guaranteed order in nested dict, it's not possible
    # to check reliably for values, but at least assert that all keys are added
    for product in products:
        keys = set(product.keys()) - {
            "productId",
            "quantity",
            "productName",
            "unit",
            "rowPriceNet",
            "rowPriceVat",
            "rowPriceTotal",
            "vatPercentage",
            "priceNet",
            "priceVat",
            "priceGross",
            "meta",
        }
        assert len(keys) == 0


@pytest.mark.parametrize(
    "order",
    ["additional_product_order_with_lease_order"],
    indirect=True,
)
def test_payload_add_additional_product_order(
    talpa_ecom_payment_provider: TalpaEComProvider,
    order: Order,
    default_talpa_product_accounting: list[TalpaProductAccounting],
    settings,
):
    payload = {"items": []}
    talpa_ecom_payment_provider.payload_add_products(
        payload, order, settings.LANGUAGE_CODE
    )

    assert len(payload["items"]) == 1
    item = payload["items"][0]

    assert payload["priceNet"] == rounded(order.total_pretax_price, as_string=True)
    assert (
        payload["priceTotal"]
        == rounded(order.total_price, as_string=True)
        == item.get("rowPriceTotal", "0")
        == item.get("priceGross", "0")
    )
    assert payload["priceVat"] == str(
        rounded(order.total_price) - rounded(order.total_pretax_price)
    )


@pytest.mark.parametrize(
    "order_with_products",
    ["berth_order", "winter_storage_order", "unmarked_winter_storage_order"],
    indirect=True,
)
def test_payload_add_place_products(
    talpa_ecom_payment_provider: TalpaEComProvider,
    order_with_products: Order,
    default_talpa_product_accounting: list[TalpaProductAccounting],
    settings,
):
    payload = {"items": []}
    area = resolve_area(order_with_products)
    talpa_ecom_payment_provider.payload_add_place_product(
        payload, order_with_products, area, settings.LANGUAGE_CODE
    )

    area = resolve_area(order_with_products)
    place = resolve_order_place(order_with_products.lease)
    is_section = isinstance(place, WinterStorageSection)
    is_berth = isinstance(place, Berth)

    expected_product_name = (
        "Berth product"
        if is_berth
        else "Winter storage product"
        if is_section
        else "Winter storage place product"
    )

    assert len(payload["items"]) == 1

    item = payload["items"][0]

    payload_meta = item.pop("meta", [])
    assert len(payload_meta) == 4 if is_berth else 1 if is_section else 3

    assert {
        "key": "placeLocation",
        "value": area.street_address,
        "label": str(place or area),
        "visibleInCheckout": True,
        "ordinal": "1",
    } in payload_meta

    if not is_section:
        assert {
            "key": "placeWidth",
            "value": "Width (m): "
            + str(place.berth_type.width if is_berth else place.place_type.width),
            "visibleInCheckout": True,
            "ordinal": "2",
        } in payload_meta
        assert {
            "key": "placeLength",
            "value": "Length (m): "
            + str(place.berth_type.length if is_berth else place.place_type.length),
            "visibleInCheckout": True,
            "ordinal": "3",
        } in payload_meta

    if is_berth:
        assert {
            "key": "placeMooring",
            "value": "Mooring: "
            + BerthMooringType(place.berth_type.mooring_type).label,
            "visibleInCheckout": True,
            "ordinal": "4",
        } in payload_meta

    assert item["rowPriceTotal"] == rounded(
        Decimal(item["rowPriceNet"]) + Decimal(item["rowPriceVat"]),
        as_string=True,
    )
    assert item["priceGross"] == rounded(
        Decimal(item["priceNet"]) + Decimal(item["priceVat"]),
        as_string=True,
    )

    assert item["productId"] == resolve_product_talpa_ecom_id(
        order_with_products.product, area
    )
    assert item["productName"] == expected_product_name
    assert item["quantity"] == 1
    assert item["unit"] == "pcs"


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order", "unmarked_winter_storage_order"],
    indirect=True,
)
def test_payload_add_customer_order_with_application(
    talpa_ecom_payment_provider: TalpaEComProvider, order: Order
):
    order.customer_first_name = None
    order.customer_last_name = None
    order.customer_email = None
    order.save()

    payload = {}
    talpa_ecom_payment_provider.payload_add_customer(payload, order)
    application = order.lease.application

    assert payload["customer"] == {
        "firstName": application.first_name.capitalize(),
        "lastName": application.last_name.capitalize(),
        "email": application.email.strip(),
        "phone": application.phone_number.strip(),
    }


@pytest.mark.parametrize(
    "order",
    ["empty_order"],
    indirect=True,
)
def test_payload_add_customer_order_without_application(
    talpa_ecom_payment_provider: TalpaEComProvider, order: Order
):
    payload = {}
    talpa_ecom_payment_provider.payload_add_customer(payload, order)

    assert payload["customer"] == {
        "firstName": order.customer_first_name.capitalize(),
        "lastName": order.customer_last_name.capitalize(),
        "email": order.customer_email.strip(),
        "phone": order.customer_phone.strip(),
    }


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_handle_notify_request_settles_order(
    talpa_ecom_provider_base_config: dict,
    order: Order,
    rf,
):
    """Test request helper reacts to transaction status update error by returning a failure url"""
    order.status = OrderStatus.OFFERED
    order.talpa_ecom_id = "c748b9cb-c2da-4340-a746-fe44fec9cc64"
    order.save()

    payload = {
        "paymentId": "36985766-eb07-42c2-8277-9508630f42d1",
        "orderId": "c748b9cb-c2da-4340-a746-fe44fec9cc64",
        "namespace": "venepaikat",
        "eventType": TALPA_ECOM_WEBHOOK_EVENT_PAYMENT_PAID,
        "timestamp": "2021-10-19T09:11:00.123Z",
    }
    request = rf.post("/payments/notify/", data=payload)

    payment_provider = create_talpa_ecom_provider(
        talpa_ecom_provider_base_config, request
    )

    with mock.patch.object(
        payment_provider,
        "get_payment_details",
        lambda _x: TalpaEComPaymentDetails(
            {"status": TalpaEComPaymentDetails.PAYMENT_PAID}
        ),
    ):
        returned = payment_provider.handle_notify_request()

    # Check that the order status didn't change
    order.refresh_from_db()
    order.lease.refresh_from_db()
    order.lease.application.refresh_from_db()

    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204

    assert order.status == OrderStatus.PAID
    assert order.lease.status == LeaseStatus.PAID
    assert order.lease.application.status == ApplicationStatus.HANDLED


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
@pytest.mark.parametrize(
    "event_type",
    TALPA_ECOM_WEBHOOK_EVENT_TYPES,
)
def test_handle_notify_request_order_does_not_exist(
    talpa_ecom_provider_base_config: dict, order: Order, event_type: str, rf
):
    order.status = OrderStatus.OFFERED
    order.save()

    payload = {
        "orderId": uuid4(),
        "eventType": event_type,
        "namespace": "venepaikat",
    }

    request = rf.post("/payments/notify/", data=payload)
    payment_provider = create_talpa_ecom_provider(
        talpa_ecom_provider_base_config, request
    )

    returned = payment_provider.handle_notify_request()

    # Check that the order status didn't change
    order.refresh_from_db()
    assert order.status == OrderStatus.OFFERED

    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 404


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_handle_notify_request_wrong_namespace(
    talpa_ecom_provider_base_config: dict, order: Order, rf
):
    """Test request helper changes the order status to PAID

    Also check it returns a success url with order number"""
    order.status = OrderStatus.OFFERED
    order.talpa_ecom_id = "c748b9cb-c2da-4340-a746-fe44fec9cc64"
    order.save()

    payload = {
        "paymentId": "36985766-eb07-42c2-8277-9508630f42d1",
        "orderId": "c748b9cb-c2da-4340-a746-fe44fec9cc64",
        "namespace": "WRONG-NAMESPACE",
        "eventType": TALPA_ECOM_WEBHOOK_EVENT_PAYMENT_PAID,
        "timestamp": "2021-10-19T09:11:00.123Z",
    }

    request = rf.post("/payments/notify/", data=payload)
    payment_provider = create_talpa_ecom_provider(
        talpa_ecom_provider_base_config, request
    )
    returned = payment_provider.handle_notify_request()

    order_after = Order.objects.get(talpa_ecom_id=payload["orderId"])

    # Check that the order status didn't change
    assert order_after.status == OrderStatus.OFFERED

    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 400


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_handle_notify_request_wrong_event_type(
    talpa_ecom_provider_base_config: dict, order: Order, rf
):
    """Test request helper changes the order status to PAID

    Also check it returns a success url with order number"""
    order.status = OrderStatus.OFFERED
    order.talpa_ecom_id = "c748b9cb-c2da-4340-a746-fe44fec9cc64"
    order.save()

    payload = {
        "paymentId": "36985766-eb07-42c2-8277-9508630f42d1",
        "orderId": "c748b9cb-c2da-4340-a746-fe44fec9cc64",
        "namespace": "venepaikat",
        "eventType": "WRONG_TYPE",
        "timestamp": "2021-10-19T09:11:00.123Z",
    }

    request = rf.post("/payments/notify/", data=payload)
    payment_provider = create_talpa_ecom_provider(
        talpa_ecom_provider_base_config, request
    )
    returned = payment_provider.handle_notify_request()

    order_after = Order.objects.get(talpa_ecom_id=payload["orderId"])

    # Check that the order status didn't change
    assert order_after.status == OrderStatus.OFFERED

    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 400


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
@pytest.mark.parametrize(
    "event_type,status",
    [
        (
            TALPA_ECOM_WEBHOOK_EVENT_PAYMENT_PAID,
            TalpaEComPaymentDetails.PAYMENT_CANCELLED,
        ),
        (
            TALPA_ECOM_WEBHOOK_EVENT_ORDER_CANCELLED,
            TalpaEComPaymentDetails.PAYMENT_PAID,
        ),
    ],
)
def test_handle_notify_request_wrong_payment_status(
    talpa_ecom_provider_base_config: dict,
    order: Order,
    event_type: str,
    status: str,
    rf,
):
    """Test request helper changes the order status to PAID

    Also check it returns a success url with order number"""
    order.status = OrderStatus.OFFERED
    order.talpa_ecom_id = "c748b9cb-c2da-4340-a746-fe44fec9cc64"
    order.save()

    payload = {
        "paymentId": "36985766-eb07-42c2-8277-9508630f42d1",
        "orderId": "c748b9cb-c2da-4340-a746-fe44fec9cc64",
        "namespace": "venepaikat",
        "eventType": event_type,
        "timestamp": "2021-10-19T09:11:00.123Z",
    }

    request = rf.post("/payments/notify/", data=payload)
    payment_provider = create_talpa_ecom_provider(
        talpa_ecom_provider_base_config, request
    )

    with mock.patch.object(
        payment_provider,
        "get_payment_details",
        lambda _x: TalpaEComPaymentDetails({"status": status}),
    ):
        returned = payment_provider.handle_notify_request()

    # Check that the order status didn't change
    order.refresh_from_db()
    assert order.status == OrderStatus.OFFERED

    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 400


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_handle_notify_request_order_cancelled(
    talpa_ecom_provider_base_config: dict, order: Order, rf
):
    order.status = OrderStatus.OFFERED
    order.talpa_ecom_id = "c748b9cb-c2da-4340-a746-fe44fec9cc64"
    order.save()

    payload = {
        "orderId": "c748b9cb-c2da-4340-a746-fe44fec9cc64",
        "namespace": "venepaikat",
        "eventType": TALPA_ECOM_WEBHOOK_EVENT_ORDER_CANCELLED,
        "timestamp": "2021-10-19T09:11:00.123Z",
    }

    request = rf.post("/payments/notify/", data=payload)
    payment_provider = create_talpa_ecom_provider(
        talpa_ecom_provider_base_config, request
    )

    with mock.patch.object(
        payment_provider,
        "get_payment_details",
        lambda _x: TalpaEComPaymentDetails(
            {"status": TalpaEComPaymentDetails.PAYMENT_CANCELLED}
        ),
    ):
        returned = payment_provider.handle_notify_request()

    # Check that the order status didn't change
    order.refresh_from_db()
    order.lease.refresh_from_db()
    order.lease.application.refresh_from_db()

    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204

    assert order.status == OrderStatus.REJECTED
    assert order.lease.status == LeaseStatus.REFUSED
    assert order.lease.application.status == ApplicationStatus.REJECTED


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_get_payment_details(
    talpa_ecom_payment_provider: TalpaEComProvider, order: Order
):
    order.talpa_ecom_id = "abc55f14-36e3-3f97-a71b-f79b8a9811d5"
    order.save()
    payment_data = {
        "paymentId": "abc55f14-36e3-3f97-a71b-f79b8a9811d5_at_20211117-112134",
        "namespace": "asukaspysakointi",
        "orderId": "abc55f14-36e3-3f97-a71b-f79b8a9811d5",
        "userId": "Keshaun39",
        "status": "payment_created",
        "paymentMethod": "nordea",
        "paymentType": "order",
        "totalExclTax": 100,
        "total": 124,
        "taxAmount": 24,
        "description": None,
        "additionalInfo": '{"payment_method": nordea}',
        "token": "ebb26c00f2e02919a1af2fe14affe3d8399e2f7f4352ca50e7b5de2ebf5a07e2",
        "timestamp": "20211117-112135",
        "paymentMethodLabel": "Nordea",
    }

    mocked_response = MockResponse(
        data=payment_data,
        status_code=200,
    )

    with mock.patch(
        "payments.providers.talpa_ecom.requests.get",
        side_effect=lambda _url, **kwargs: mocked_response,
    ):
        response = talpa_ecom_payment_provider.get_payment_details(order)

    assert response == TalpaEComPaymentDetails(payment_data)
