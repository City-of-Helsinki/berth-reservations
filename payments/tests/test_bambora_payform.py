import hmac
from unittest import mock

import pytest
from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from django.test.client import RequestFactory
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from payments.enums import OrderStatus
from payments.models import Order, OrderToken
from payments.providers.bambora_payform import (
    DuplicateOrderError,
    PayloadValidationError,
    ServiceUnavailableError,
    UnknownReturnCodeError,
    VENE_PAYMENTS_BAMBORA_API_KEY,
)
from payments.tests.conftest import (
    create_bambora_provider,
    FAKE_BAMBORA_API_URL,
    mocked_response_create,
)
from payments.tests.factories import BerthProductFactory, OrderFactory
from payments.utils import get_talpa_product_id, price_as_fractional_int


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_initiate_payment_success(provider_base_config: dict, order: Order):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()

    payment_provider = create_bambora_provider(provider_base_config, request)
    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ) as mock_call:
        url = payment_provider.initiate_payment(order)
        assert url.startswith(payment_provider.url_payment_api)
        assert "token/abc123" in url
        # Verify that the return URL passed includes the application language
        assert order.lease.application.language in mock_call.call_args.kwargs.get(
            "json"
        ).get("payment_method").get("return_url")


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_initiate_payment_error_unavailable(provider_base_config, order: Order):
    """Test the request creator raises service unavailable if request doesn't go through"""
    request = RequestFactory().request()

    invalid_config = {
        **provider_base_config,
        "VENE_PAYMENTS_BAMBORA_API_URL": FAKE_BAMBORA_API_URL,
    }
    unavailable_payment_provider = create_bambora_provider(invalid_config, request)

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ):
        with pytest.raises(ServiceUnavailableError):
            unavailable_payment_provider.initiate_payment(order)


def test_handle_initiate_payment_success(order, payment_provider):
    """Test the response handler recognizes success and adds token as part of the returned url"""
    r = {"result": 0, "token": "abc123", "type": "e-payment"}
    return_value = payment_provider.handle_initiate_payment(order, r)
    assert r["token"] in return_value


def test_handle_initiate_payment_error_validation(order, payment_provider):
    """Test the response handler raises PayloadValidationError as expected"""
    r = {"result": 1, "type": "e-payment", "errors": ["Invalid auth code"]}
    with pytest.raises(PayloadValidationError):
        payment_provider.handle_initiate_payment(order, r)


def test_handle_initiate_payment_error_duplicate(order, payment_provider):
    """Test the response handler raises DuplicateOrderError as expected"""
    r = {"result": 2, "type": "e-payment"}
    with pytest.raises(DuplicateOrderError):
        payment_provider.handle_initiate_payment(order, r)


def test_handle_initiate_payment_error_unavailable(order, payment_provider):
    """Test the response handler raises ServiceUnavailableError as expected"""
    r = {"result": 10, "type": "e-payment"}
    with pytest.raises(ServiceUnavailableError):
        payment_provider.handle_initiate_payment(order, r)


def test_handle_initiate_payment_error_unknown_code(order, payment_provider):
    """Test the response handler raises UnknownReturnCodeError as expected"""
    r = {"result": 15, "type": "e-payment", "test": "unrecognized extra stuff"}
    with pytest.raises(UnknownReturnCodeError):
        payment_provider.handle_initiate_payment(order, r)


@pytest.mark.parametrize(
    "order_with_products", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_payload_add_products_success(payment_provider, order_with_products: Order):
    """Test the products and total order price data is added correctly into payload"""
    payload = {}
    payment_provider.payload_add_products(
        payload, order_with_products, order_with_products.lease.application.language
    )
    assert "amount" in payload
    assert payload.get("amount") == price_as_fractional_int(
        order_with_products.total_price
    )

    assert "products" in payload
    products = payload.get("products")
    assert len(products) == 5  # 1 place product + 4 additional products
    # As there's no guaranteed order in nested dict, it's not possible
    # to check reliably for values, but at least assert that all keys are added
    for product in products:
        assert "id" in product
        assert "title" in product
        assert "price" in product
        assert "pretax_price" in product
        assert "tax" in product
        assert "count" in product
        assert "type" in product


def test_payload_add_product_default_berth_product(payment_provider, berth_lease):
    product = BerthProductFactory(harbor=None)
    order = OrderFactory(
        customer=berth_lease.customer, lease=berth_lease, product=product
    )
    payload = {}
    payment_provider.payload_add_products(payload, order, "fi")
    assert "amount" in payload
    assert payload.get("products")[0].get("id") == get_talpa_product_id(
        product.id, area=berth_lease.berth.pier.harbor
    )


@pytest.mark.parametrize(
    "order_with_products", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_payload_add_customer_success(payment_provider, order_with_products: Order):
    """Test the customer data from order is added correctly into payload"""
    payload = {}
    payment_provider.payload_add_customer(payload, order_with_products)

    assert "email" in payload
    assert payload.get("email") == order_with_products.lease.application.email

    assert "customer" in payload
    customer = payload.get("customer")
    assert (
        customer.get("firstname")
        == order_with_products.lease.application.first_name.capitalize()
    )
    assert (
        customer.get("lastname")
        == order_with_products.lease.application.last_name.capitalize()
    )
    assert customer.get("email") == order_with_products.lease.application.email
    assert (
        customer.get("address_street") == order_with_products.lease.application.address
    )
    assert customer.get("address_zip") == order_with_products.lease.application.zip_code
    assert (
        customer.get("address_city")
        == order_with_products.lease.application.municipality.capitalize()
    )


def test_payload_add_auth_code_success(payment_provider, order):
    """Test the auth code is added correctly into the payload"""
    payload = {
        "api_key": payment_provider.config.get(VENE_PAYMENTS_BAMBORA_API_KEY),
        "order_number": order.order_number,
    }
    payment_provider.payload_add_auth_code(payload)
    assert "authcode" in payload
    assert payload.get("authcode") == payment_provider.calculate_auth_code(
        f'{payload["api_key"]}|{payload["order_number"]}'
    )


def test_calculate_auth_code_success(payment_provider):
    """Test the auth code calculation returns a correct hash"""
    data = "dummy-key|abc123"
    calculated_code = payment_provider.calculate_auth_code(data)
    assert hmac.compare_digest(
        calculated_code,
        "A8894068C4E17BFD55E68B2148CF555800773C673D19FA0648101C1E9CF5D0CE",
    )


def test_check_new_payment_authcode_success(payment_provider):
    """Test the helper is able to extract necessary values from a request and compare authcodes"""
    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462",
        "RETURN_CODE": "0",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    assert payment_provider.check_new_payment_authcode(request)


def test_check_new_payment_authcode_invalid(payment_provider):
    """Test the helper fails when params do not match the auth code"""
    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462",
        "RETURN_CODE": "0",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "0",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    assert not payment_provider.check_new_payment_authcode(request)


def test_handle_success_request_return_url_missing(provider_base_config, order):
    """Test the handler returns a bad request object if return URL is missing from params"""
    params = {
        "AUTHCODE": "905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462",
        "RETURN_CODE": "0",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "0",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)

    returned = payment_provider.handle_success_request()
    assert isinstance(returned, HttpResponseServerError)
    assert returned.status_code == 500


def test_handle_success_request_order_not_found(provider_base_config, order):
    """Test request helper returns a failure url when order can't be found"""
    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "83F6C12E8D894B433CB2B6A2A56709CF0AE26665768ED74FB28922F6ED128301",
        "RETURN_CODE": "0",
        "ORDER_NUMBER": "abc567",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_success_request()
    assert isinstance(returned, HttpResponse)
    assert "payment_status=failure" in returned.url


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_handle_success_request_success(provider_base_config, order: Order):
    """Test request helper changes the order status to PAID

    Also check it returns a success url with order number"""
    order.status = OrderStatus.WAITING
    order.order_number = "abc123"
    order.save()

    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462",
        "RETURN_CODE": "0",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_success_request()

    order_after = Order.objects.get(order_number=params.get("ORDER_NUMBER"))
    assert order_after.status == OrderStatus.PAID
    assert order_after.lease.application.status == ApplicationStatus.HANDLED

    assert isinstance(returned, HttpResponse)
    url = returned.url
    assert "/payment-result" in url
    assert "payment_status=success" in url


def test_handle_success_request_payment_failed(provider_base_config, order):
    """Test request helper changes the order status to rejected and returns a failure url"""
    order.status = OrderStatus.WAITING
    order.order_number = "abc123"
    order.save()

    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "ED754E8F2E7FE0CC269B9F6A1C197F19B8393F37A1B63BE1E889D53F87A5FCA1",
        "RETURN_CODE": "1",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_success_request()
    order_after = Order.objects.get(order_number=params.get("ORDER_NUMBER"))
    assert order_after.status == OrderStatus.WAITING
    assert isinstance(returned, HttpResponse)
    assert "payment_status=failure" in returned.url


def test_handle_success_request_status_not_updated(provider_base_config, order):
    """Test request helper reacts to transaction status update error by returning a failure url"""
    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "D9170B2C0C0F36E467517E0DF2FC7D89BBC7237597B6BE3B0DE11518F93D7342",
        "RETURN_CODE": "4",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_success_request()
    # TODO Handling isn't final yet so there might be something extra that needs to be tested here
    assert isinstance(returned, HttpResponse)
    assert "payment_status=failure" in returned.url


def test_handle_success_request_maintenance_break(provider_base_config, order):
    """Test request helper reacts to maintenance break error by returning a failure url"""
    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "144662CEBD9861D4526C4147D10FB6C50FE1E02453701F8972B699CFD1F4A99E",
        "RETURN_CODE": "10",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_success_request()
    # TODO Handling isn't final yet so there might be something extra that needs to be tested here
    assert isinstance(returned, HttpResponse)
    assert "payment_status=failure" in returned.url


def test_handle_success_request_unknown_error(provider_base_config, order):
    """Test request helper returns a failure url when status code is unknown"""
    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "3CD17A51E89C0A6DDDCA743AFCBD5DC40E8FF8AB97756089E75EC953A19A938C",
        "RETURN_CODE": "15",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/success/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_success_request()
    assert isinstance(returned, HttpResponse)
    assert "payment_status=failure" in returned.url


def test_handle_notify_request_order_not_found(provider_base_config, order):
    """Test request notify helper returns http 204 when order can't be found"""
    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "83F6C12E8D894B433CB2B6A2A56709CF0AE26665768ED74FB28922F6ED128301",
        "RETURN_CODE": "0",
        "ORDER_NUMBER": "abc567",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/notify/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_notify_request()
    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204


@pytest.mark.parametrize(
    "order_status, expected_order_status",
    (
        (OrderStatus.WAITING, OrderStatus.PAID),
        (OrderStatus.PAID, OrderStatus.PAID),
        (OrderStatus.REJECTED, OrderStatus.PAID),
        (OrderStatus.EXPIRED, OrderStatus.EXPIRED),
        (OrderStatus.CANCELLED, OrderStatus.CANCELLED),
    ),
)
def test_handle_notify_request_success(
    provider_base_config,
    berth_order: Order,
    order_status: OrderStatus,
    expected_order_status: OrderStatus,
):
    """Test request notify helper returns http 204 and order status is correct when successful"""
    berth_order.order_number = "abc123"
    berth_order.status = order_status
    berth_order.save()

    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462",
        "RETURN_CODE": "0",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/notify/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_notify_request()
    order_after = Order.objects.get(order_number=params.get("ORDER_NUMBER"))
    assert order_after.status == expected_order_status
    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204


@pytest.mark.parametrize(
    "order_status, expected_order_status",
    (
        (OrderStatus.WAITING, OrderStatus.REJECTED),
        (OrderStatus.REJECTED, OrderStatus.REJECTED),
        (OrderStatus.EXPIRED, OrderStatus.EXPIRED),
        (OrderStatus.PAID, OrderStatus.PAID),
    ),
)
def test_handle_notify_request_payment_failed(
    provider_base_config, order, order_status, expected_order_status
):
    """Test request notify helper returns http 204 and order status is correct when payment fails"""
    order.order_number = "abc123"
    order.status = order_status
    order.save()

    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "ED754E8F2E7FE0CC269B9F6A1C197F19B8393F37A1B63BE1E889D53F87A5FCA1",
        "RETURN_CODE": "1",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }

    rf = RequestFactory()
    request = rf.get("/payments/notify/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_notify_request()
    order_after = Order.objects.get(order_number=params.get("ORDER_NUMBER"))
    assert order_after.status == expected_order_status
    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204


def test_handle_notify_request_unknown_error(provider_base_config, order):
    """Test request notify helper returns http 204 when status code is unknown"""
    params = {
        "VENE_UI_RETURN_URL": "http%3A%2F%2F127.0.0.1%3A8000%2Fv1",
        "AUTHCODE": "3CD17A51E89C0A6DDDCA743AFCBD5DC40E8FF8AB97756089E75EC953A19A938C",
        "RETURN_CODE": "15",
        "ORDER_NUMBER": "abc123",
        "SETTLED": "1",
    }
    rf = RequestFactory()
    request = rf.get("/payments/notify/", params)
    payment_provider = create_bambora_provider(provider_base_config, request)
    returned = payment_provider.handle_notify_request()
    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204


def test_get_payment_email_url(provider_base_config, order):
    request = RequestFactory().request()
    payment_provider = create_bambora_provider(provider_base_config, request)
    lang = "fi"
    url = payment_provider.get_payment_email_url(order, lang)
    ui_return_url = settings.VENE_UI_RETURN_URL

    assert (
        url
        == f"{ui_return_url.format(LANG=lang)}/payment?order_number={order.order_number}"
    )


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_initiate_duplicated_payment(provider_base_config, order):
    request = RequestFactory().request()

    payment_provider = create_bambora_provider(provider_base_config, request)
    assert OrderToken.objects.count() == 0

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ) as mock_call:
        payment_provider.initiate_payment(order)
        assert OrderToken.objects.count() == 1
        url = payment_provider.initiate_payment(order)
        # Verify that the return URL passed includes the application language
        assert order.lease.application.language in mock_call.call_args.kwargs.get(
            "json"
        ).get("payment_method").get("return_url")

    assert OrderToken.objects.count() == 1
    assert OrderToken.objects.first().order == order

    assert url.startswith(payment_provider.url_payment_api)
    assert "token/abc123" in url


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
@freeze_time("2019-01-14T08:00:00Z")
def test_initiate_duplicated_payment_new_token_after_expiry(
    provider_base_config, order
):
    request = RequestFactory().request()

    payment_provider = create_bambora_provider(provider_base_config, request)
    assert OrderToken.objects.count() == 0

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ) as mock_call:
        payment_provider.initiate_payment(order)
        assert OrderToken.objects.count() == 1
        token = OrderToken.objects.first()

        assert token.order == order
        assert token.valid_until.isoformat() == "2019-01-20T21:59:59.999999+00:00"

        # Try to pay again 7 days after the day when the payment was created
        with freeze_time("2019-01-21T08:00:00Z"):
            url = payment_provider.initiate_payment(order)

        # Verify that the return URL passed includes the application language
        assert order.lease.application.language in mock_call.call_args.kwargs.get(
            "json"
        ).get("payment_method").get("return_url")

    assert OrderToken.objects.count() == 2

    assert url.startswith(payment_provider.url_payment_api)
    assert "token/abc123" in url
