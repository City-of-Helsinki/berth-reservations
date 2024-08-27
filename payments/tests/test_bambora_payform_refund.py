from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test.client import RequestFactory
from django.utils.timezone import now

from berth_reservations.tests.utils import MockResponse
from leases.enums import LeaseStatus
from payments.enums import OrderRefundStatus, OrderStatus
from payments.exceptions import RefundPriceError
from payments.models import Order, OrderRefund, OrderToken
from payments.providers.bambora_payform import (
    PayloadValidationError,
    ServiceUnavailableError,
)
from payments.tests.conftest import (
    create_bambora_provider,
    FAKE_BAMBORA_API_URL,
    mocked_bambora_response_create,
    mocked_refund_payment_details,
    mocked_refund_response_create,
)
from payments.tests.factories import OrderRefundFactory
from payments.utils import (
    convert_aftertax_to_pretax,
    currency_format,
    get_talpa_product_id,
    price_as_fractional_int,
)
from utils.numbers import rounded

# Skip all tests in this module
pytest.skip("Bambora is dead code and should be removed", allow_module_level=True)

notify_success_params = {
    "AUTHCODE": "9C60B3077276A38495E2D785D1B5E6A293427BC4025E5C39AB870EA4CF187E0B",
    "RETURN_CODE": "0",
    "REFUND_ID": "1234567",
}

success_refund_params = {"result": 0, "type": "instant", "refund_id": 2587411}


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_refund_success(bambora_provider_base_config: dict, order: Order):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()
    order.status = OrderStatus.PAID
    order.lease.status = LeaseStatus.PAID
    order.lease.save()
    order.save()

    OrderToken.objects.create(
        order=order, token="98765", valid_until=now() - relativedelta(hours=1)
    )
    valid_token = OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )
    if hasattr(order.product, "price_for_tier"):
        place_price = order.product.price_for_tier(order.lease.berth.pier.price_tier)
        area = order.lease.berth.pier.harbor
    else:
        # Winter products are priced per m2
        place_price = rounded(
            order.product.price_value
            * order.lease.place.place_type.width
            * order.lease.place.place_type.length,
        )
        area = order.lease.place.winter_storage_section.area

    products = [
        {
            "id": get_talpa_product_id(
                order.product.id, order.product.tax_percentage, area, False
            ),
            "product_id": 1123,
            "title": order.product.name,
            "count": 1,
            "pretax_price": price_as_fractional_int(
                convert_aftertax_to_pretax(place_price, order.product.tax_percentage)
            ),
            "tax": int(order.product.tax_percentage),
            "price": str(price_as_fractional_int(place_price)),
            "type": 1,
        }
    ]

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)
    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_refund_response_create,
    ) as mock_call, mock.patch(
        "payments.providers.bambora_payform.BamboraPayformProvider.get_payment_details",
        side_effect=mocked_refund_payment_details(products=products),
    ):
        refund = payment_provider.initiate_refund(order)

    assert refund.refund_id == "123456"
    assert refund.order == order
    assert refund.status == OrderRefundStatus.PENDING
    assert refund.amount == order.total_price

    args = mock_call.call_args.kwargs.get("json")
    assert (
        args.get("order_number")
        == f"{order.order_number}-{valid_token.created_at.timestamp()}"
    )


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_refund_no_order_email(
    bambora_provider_base_config: dict, order: Order
):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()
    order.status = OrderStatus.PAID
    order.email = None
    order.lease.status = LeaseStatus.PAID
    order.lease.save()
    order.save()

    OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )

    if hasattr(order.product, "price_for_tier"):
        place_price = order.product.price_for_tier(order.lease.berth.pier.price_tier)
        area = order.lease.berth.pier.harbor
    else:
        # Winter products are priced per m2
        place_price = rounded(
            order.product.price_value
            * order.lease.place.place_type.width
            * order.lease.place.place_type.length,
        )
        area = order.lease.place.winter_storage_section.area

    products = [
        {
            "id": get_talpa_product_id(
                order.product.id, order.product.tax_percentage, area, False
            ),
            "product_id": 1123,
            "title": order.product.name,
            "count": 1,
            "pretax_price": price_as_fractional_int(
                convert_aftertax_to_pretax(place_price, order.product.tax_percentage)
            ),
            "tax": int(order.product.tax_percentage),
            "price": price_as_fractional_int(place_price),
            "type": 1,
        }
    ]

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)
    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_refund_response_create,
    ), mock.patch(
        "payments.providers.bambora_payform.BamboraPayformProvider.get_payment_details",
        side_effect=mocked_refund_payment_details(products=products),
    ):
        refund = payment_provider.initiate_refund(order)

    assert refund.refund_id == "123456"


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_refund_refunded_amount_does_not_match(
    bambora_provider_base_config: dict, order: Order
):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()
    order.status = OrderStatus.PAID
    order.lease.status = LeaseStatus.PAID
    order.lease.save()
    order.save()

    OrderToken.objects.create(
        order=order, token="98765", valid_until=now() - relativedelta(hours=1)
    )
    OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )
    place_price = order.total_price + 10

    products = [
        {
            "id": "123123123",
            "product_id": 1123,
            "title": order.product.name,
            "count": 1,
            "pretax_price": price_as_fractional_int(
                convert_aftertax_to_pretax(place_price, order.product.tax_percentage)
            ),
            "tax": int(order.product.tax_percentage),
            "price": price_as_fractional_int(place_price),
            "type": 1,
        }
    ]

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)
    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_refund_response_create,
    ), mock.patch(
        "payments.providers.bambora_payform.BamboraPayformProvider.get_payment_details",
        side_effect=mocked_refund_payment_details(products=products),
    ), pytest.raises(
        RefundPriceError
    ) as exception:
        payment_provider.initiate_refund(order)

    assert (
        f"The amount to be refunded ({currency_format(place_price)}) "
        f"does not match the amount paid ({currency_format(order.total_price)})"
    ) in str(exception)
    assert not OrderRefund.objects.exists()


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_refund_another_pending_refund(
    bambora_provider_base_config: dict, order: Order
):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()
    order.status = OrderStatus.PAID
    order.lease.status = LeaseStatus.PAID
    order.lease.save()
    order.save()
    OrderRefundFactory(order=order, status=OrderRefundStatus.PENDING)

    OrderToken.objects.create(
        order=order, token="98765", valid_until=now() - relativedelta(hours=1)
    )
    OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )

    products = [
        {
            "id": "123123123",
            "product_id": 1123,
            "title": order.product.name,
            "count": 1,
            "pretax_price": 100,
            "tax": 24,  # DEPRECATED! Bambora
            "price": 100,
            "type": 1,
        }
    ]

    assert OrderRefund.objects.count() == 1

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)
    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_refund_response_create,
    ), mock.patch(
        "payments.providers.bambora_payform.BamboraPayformProvider.get_payment_details",
        side_effect=mocked_refund_payment_details(products=products),
    ), pytest.raises(
        ValidationError
    ) as exception:
        payment_provider.initiate_refund(order)

    assert "Cannot refund an order that has another pending refund" in str(exception)
    assert OrderRefund.objects.count() == 1


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_refund_no_order_email_or_application(
    bambora_provider_base_config: dict, order: Order
):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()
    order.status = OrderStatus.PAID
    order.customer_email = None
    order.lease.status = LeaseStatus.PAID
    order.lease.application = None
    order.lease.save()
    order.save()

    OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)
    with pytest.raises(ValidationError) as exception:
        payment_provider.initiate_refund(order)

    assert "Cannot refund an order that has no email" in str(exception)


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_refund_token_still_valid(
    bambora_provider_base_config: dict, order: Order
):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()
    order.status = OrderStatus.PAID
    order.lease.status = LeaseStatus.PAID
    order.lease.save()
    order.save()

    OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )
    OrderToken.objects.create(
        order=order, token="98765", valid_until=now() + relativedelta(hours=1)
    )

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)
    with pytest.raises(ValidationError) as exception:
        payment_provider.initiate_refund(order)

    assert "Cannot refund an order that has not been settled yet (active token)" in str(
        exception
    )


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
@pytest.mark.parametrize(
    "order_status",
    [
        OrderStatus.CANCELLED,
        OrderStatus.ERROR,
        OrderStatus.EXPIRED,
        OrderStatus.PAID_MANUALLY,
        OrderStatus.REFUNDED,
        OrderStatus.REJECTED,
        OrderStatus.DRAFTED,
        OrderStatus.OFFERED,
    ],
)
def test_initiate_refund_invalid_order_status(
    bambora_provider_base_config: dict, order: Order, order_status
):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()
    order.status = order_status
    order.save()

    OrderToken.objects.create(
        order=order, token="98765", valid_until=now() - relativedelta(hours=1)
    )
    OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)
    with pytest.raises(ValidationError) as exception:
        payment_provider.initiate_refund(order)

    assert "Cannot refund an order that is not paid" in str(exception)


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
@pytest.mark.parametrize(
    "lease_status",
    [
        LeaseStatus.DRAFTED,
        LeaseStatus.ERROR,
        LeaseStatus.EXPIRED,
        LeaseStatus.OFFERED,
        LeaseStatus.TERMINATED,
    ],
)
def test_initiate_refund_invalid_lease_status(
    bambora_provider_base_config: dict, order: Order, lease_status
):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    request = RequestFactory().request()
    order.status = OrderStatus.PAID
    order.lease.status = lease_status
    order.lease.save()
    order.save()

    OrderToken.objects.create(
        order=order, token="98765", valid_until=now() - relativedelta(hours=1)
    )
    OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)
    with pytest.raises(ValidationError) as exception:
        payment_provider.initiate_refund(order)

    assert "Cannot refund an order that is not paid" in str(exception)


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_initiate_refund_error_unavailable(bambora_provider_base_config, order: Order):
    """Test the request creator raises service unavailable if request doesn't go through"""
    request = RequestFactory().request()

    invalid_config = {
        **bambora_provider_base_config,
        "VENE_PAYMENTS_BAMBORA_API_URL": FAKE_BAMBORA_API_URL,
    }
    unavailable_payment_provider = create_bambora_provider(invalid_config, request)

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_bambora_response_create,
    ):
        with pytest.raises(ServiceUnavailableError):
            unavailable_payment_provider.initiate_payment(order)


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_handle_initiate_refund_error_validation(order, bambora_provider_base_config):
    """Test the response handler raises PayloadValidationError as expected"""
    r = {"result": 1, "type": "e-payment", "errors": ["Invalid auth code"]}
    OrderToken.objects.create(
        order=order, token="12345", valid_until=now() - relativedelta(days=7)
    )
    order.status = OrderStatus.PAID
    order.customer_email = "a@b.com"
    order.lease.status = LeaseStatus.PAID
    order.lease.save()
    order.save()
    request = RequestFactory().request()

    payment_provider = create_bambora_provider(bambora_provider_base_config, request)

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=[MockResponse(data=r)],
    ):
        with pytest.raises(PayloadValidationError):
            payment_provider.initiate_refund(order)


def test_check_refund_authcode_success(bambora_payment_provider):
    """Test the helper is able to extract necessary values from a request and compare authcodes"""
    rf = RequestFactory()
    request = rf.get("/payments/notify_refund/", notify_success_params)
    assert bambora_payment_provider.check_new_refund_authcode(request)


def test_check_refund_authcode_invalid(bambora_payment_provider):
    """Test the helper fails when params do not match the auth code"""
    params = {
        "AUTHCODE": "9C60B3077276A38495E2D785D1B5E6A293427BC4025E5C39AB870EA4CF187E0B",
        "RETURN_CODE": "1",
        "REFUND_ID": "1234567",
    }
    rf = RequestFactory()
    request = rf.get("/payments/notify_refund/", params)
    assert not bambora_payment_provider.check_new_refund_authcode(request)


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_handle_notify_request_success(
    bambora_provider_base_config,
    order: Order,
):
    """Test request notify helper returns http 204 and order status is correct when successful"""
    order.order_number = "abc123"
    order.status = OrderStatus.PAID
    order.lease.status = LeaseStatus.PAID
    order.lease.save()
    order.save()
    refund = OrderRefundFactory(
        order=order, refund_id="1234567", amount=order.total_price
    )

    rf = RequestFactory()
    request = rf.get("/payments/notify_refund/", notify_success_params)
    payment_provider = create_bambora_provider(bambora_provider_base_config, request)

    assert refund.status == OrderRefundStatus.PENDING

    returned = payment_provider.handle_notify_refund_request()

    refund = OrderRefund.objects.get(refund_id=notify_success_params.get("REFUND_ID"))
    order = refund.order

    assert refund.status == OrderRefundStatus.ACCEPTED
    assert order.status == OrderStatus.REFUNDED
    assert order.lease.status == LeaseStatus.TERMINATED

    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_handle_notify_request_payment_failed(bambora_provider_base_config, order):
    """Test request notify helper returns http 204 and order status is correct when payment fails"""
    order.order_number = "abc123"
    order.status = OrderStatus.PAID
    order.save()
    refund = OrderRefundFactory(
        order=order, refund_id="1234567", amount=order.total_price
    )

    params = {
        "AUTHCODE": "8CF2D0EA9947D09B707E3C2953EF3014F1AD12D2BB0DCDBAC3ABD4601B50462B",
        "RETURN_CODE": "1",
        "REFUND_ID": "1234567",
    }

    rf = RequestFactory()
    request = rf.get("/payments/notify_refund/", params)
    payment_provider = create_bambora_provider(bambora_provider_base_config, request)

    assert refund.status == OrderRefundStatus.PENDING
    lease_status = refund.order.lease.status

    returned = payment_provider.handle_notify_refund_request()

    refund = OrderRefund.objects.get(refund_id=params.get("REFUND_ID"))
    order = refund.order

    assert refund.status == OrderRefundStatus.REJECTED
    # The order status shouldn't change
    assert order.status == OrderStatus.PAID
    assert order.lease.status == lease_status

    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204
