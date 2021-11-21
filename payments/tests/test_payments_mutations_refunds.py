import uuid
from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core import mail
from freezegun import freeze_time

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_not_enough_permissions,
)
from leases.enums import LeaseStatus
from utils.numbers import rounded
from utils.relay import to_global_id

from ..enums import OrderRefundStatus, OrderStatus
from ..models import Order, OrderToken
from ..schema.types import OrderNode
from ..utils import (
    convert_aftertax_to_pretax,
    get_talpa_product_id,
    price_as_fractional_int,
)
from .conftest import mocked_refund_payment_details, mocked_refund_response_create

REFUND_ORDER_MUTATION = """
mutation REFUND_ORDER_MUTATION($input: RefundOrderMutationInput!) {
    refundOrder(input: $input) {
        orderRefund {
            order {
                status
            }
            status
            amount
        }
    }
}"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_refund_order(
    api_client,
    order: Order,
    payment_provider,
    notification_template_order_refunded,
):
    order.status = OrderStatus.PAID
    order.customer_email = "foo@email.com"
    order.lease.status = LeaseStatus.PAID
    order.lease.save()
    order.save()
    OrderToken.objects.create(
        order=order, token="1245", valid_until=today() - relativedelta(days=7)
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
            "id": get_talpa_product_id(order.product.id, area, False),
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

    variables = {
        "orderId": to_global_id(OrderNode, order.id),
    }

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_refund_response_create,
    ), mock.patch(
        "payments.providers.bambora_payform.BamboraPayformProvider.get_payment_details",
        side_effect=mocked_refund_payment_details(products=products),
    ):
        executed = api_client.execute(REFUND_ORDER_MUTATION, input=variables)

    assert executed["data"]["refundOrder"]["orderRefund"] == {
        "order": {"status": OrderStatus.PAID.name},
        "status": OrderRefundStatus.PENDING.name,
        "amount": str(order.price),
    }

    assert len(mail.outbox) == 1
    assert (
        mail.outbox[0].subject == f"test order refunded subject: {order.order_number}!"
    )
    assert mail.outbox[0].body == f"{order.order_number} {order.price}"
    assert mail.outbox[0].to == [order.customer_email]

    assert mail.outbox[0].alternatives == [
        (f"<b>{order.order_number} {order.price}</b>", "text/html")
    ]


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_refund_order_not_enough_permissions(api_client, order):
    variables = {
        "orderId": to_global_id(OrderNode, order.id),
    }

    executed = api_client.execute(REFUND_ORDER_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


@freeze_time("2020-01-01T08:00:00Z")
def test_refund_order_does_not_exist(
    superuser_api_client,
    payment_provider,
    notification_template_orders_approved,
):
    order_id = to_global_id(OrderNode, uuid.uuid4())

    variables = {"orderId": order_id}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_refund_response_create,
    ), mock.patch(
        "payments.providers.bambora_payform.BamboraPayformProvider.get_payment_details",
        side_effect=mocked_refund_payment_details(products=[]),
    ):
        executed = superuser_api_client.execute(REFUND_ORDER_MUTATION, input=variables)

    assert_doesnt_exist("Order", executed)
