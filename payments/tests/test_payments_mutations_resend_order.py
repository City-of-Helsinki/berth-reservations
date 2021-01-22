import decimal
from unittest import mock

import pytest
from django.core import mail
from freezegun import freeze_time

from berth_reservations.tests.factories import CustomerProfileFactory
from customers.schema import ProfileNode
from customers.tests.conftest import mocked_response_profile
from leases.enums import LeaseStatus
from leases.models import WinterStorageLease
from payments.enums import OrderStatus, OrderType
from utils.relay import to_global_id

from ..models import Order
from ..schema.types import OrderNode

RESEND_ORDER_MUTATION = """
mutation RESEND_ORDER_MUTATION($input: ResendOrderMutationInput!) {
    resendOrder(input: $input) {
        failedOrders {
            id
            error
        }
        sentOrders
    }
}"""


#  "winter_storage_order"
@freeze_time("2020-10-01T08:00:00Z")
@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@pytest.mark.parametrize(
    "order", ["berth_order"], indirect=True,
)
@pytest.mark.parametrize(
    "order_has_contact_info", [True, False],
)
@pytest.mark.parametrize(
    "request_has_profile_token", [True, False],
)
def test_resend_order(
    api_client,
    order: Order,
    order_has_contact_info,
    request_has_profile_token,
    notification_template_orders_approved,
    berth_product,
    winter_storage_product,
):
    order.status = OrderStatus.WAITING
    order.order_type = OrderType.LEASE_ORDER.value
    initial_price = decimal.Decimal(
        "00.42"
    )  # a price that is different from the price in BerthProduct
    order.price = initial_price
    order_original_email = "test@kuva.hel.ninja"
    if order_has_contact_info:
        order.customer_phone = "+358505658789"
        order.customer_email = order_original_email
    else:
        order.customer_phone = ""  # trigger update from profile service
        order.customer_email = ""
    order.save()
    order.lease.status = LeaseStatus.OFFERED
    order.lease.save()
    orders = [order]

    if isinstance(order.lease, WinterStorageLease):
        winter_storage_product.winter_storage_area = (
            order.lease.get_winter_storage_area()
        )

    berth_product.min_width = decimal.Decimal("0.0")
    berth_product.max_width = decimal.Decimal("999.0")
    berth_product.tier_1_price = decimal.Decimal("100.0")
    berth_product.tier_2_price = decimal.Decimal("200.0")
    berth_product.tier_3_price = decimal.Decimal("300.0")
    berth_product.save()

    variables = {
        "orders": [to_global_id(OrderNode, o.id) for o in orders],
        "dueDate": "2020-01-31",
    }
    if request_has_profile_token:
        variables["profileToken"] = "token"

    customer_profile = CustomerProfileFactory()

    profile_data = {
        "id": to_global_id(ProfileNode, customer_profile.id),
        "first_name": order.lease.application.first_name,
        "last_name": order.lease.application.last_name,
        "primary_email": {"email": order.lease.application.email},
        "primary_phone": {"phone": order.lease.application.phone_number},
    }

    with mock.patch(
        "requests.post",
        side_effect=mocked_response_profile(
            count=0, data=profile_data, use_edges=False
        ),
    ):
        executed = api_client.execute(RESEND_ORDER_MUTATION, input=variables)

    if request_has_profile_token or order_has_contact_info:
        # there was sufficient customer info available for invoicing
        assert executed["data"]["resendOrder"]["failedOrders"] == []
        assert executed["data"]["resendOrder"]["sentOrders"] == [str(order.id)]

        order.refresh_from_db()
        assert order.price != initial_price
        order.lease.refresh_from_db()

        assert order.status == OrderStatus.WAITING
        assert order.lease.status == LeaseStatus.OFFERED

        assert len(mail.outbox) == 1
        assert (
            mail.outbox[0].subject
            == f"test order approved subject, event: {order.order_number}!"
        )
        assert order.order_number in mail.outbox[0].body

        if order_has_contact_info:
            assert mail.outbox[0].to == [order_original_email]
        else:
            assert mail.outbox[0].to == [order.lease.application.email]

        assert order.order_number in mail.outbox[0].alternatives[0][0]
        assert mail.outbox[0].alternatives[0][1] == "text/html"
    else:
        assert len(executed["data"]["resendOrder"]["failedOrders"]) == 1
        assert (
            "Profile token is required"
            in executed["data"]["resendOrder"]["failedOrders"][0]["error"]
        )
        assert executed["data"]["resendOrder"]["sentOrders"] == []
