import decimal
from unittest import mock

import pytest
from babel.dates import format_date
from django.core import mail
from freezegun import freeze_time

from berth_reservations.tests.factories import CustomerProfileFactory
from customers.schema import ProfileNode
from customers.services import SMSNotificationService
from customers.tests.conftest import mocked_response_profile
from leases.enums import LeaseStatus
from leases.models import WinterStorageLease
from payments.enums import OrderStatus, OrderType
from utils.relay import to_global_id

from ..models import Order
from ..notifications import NotificationType
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
@pytest.mark.parametrize("order_status", [OrderStatus.OFFERED, OrderStatus.ERROR])
def test_resend_order(
    api_client,
    order: Order,
    order_has_contact_info,
    request_has_profile_token,
    notification_template_orders_approved,
    berth_product,
    winter_storage_product,
    payment_provider,
    order_status,
):
    order.status = order_status
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
    ), mock.patch.object(
        SMSNotificationService, "send", return_value=None
    ) as mock_send_sms:
        executed = api_client.execute(RESEND_ORDER_MUTATION, input=variables)

    if request_has_profile_token or order_has_contact_info:
        # there was sufficient customer info available for invoicing
        assert executed["data"]["resendOrder"]["failedOrders"] == []
        assert executed["data"]["resendOrder"]["sentOrders"] == [str(order.id)]

        order.refresh_from_db()
        assert order.price != initial_price
        order.lease.refresh_from_db()

        assert order.status == OrderStatus.OFFERED
        assert order.lease.status == LeaseStatus.OFFERED

        assert len(mail.outbox) == 1
        assert (
            mail.outbox[0].subject
            == f"test order approved subject, event: {order.order_number}!"
        )
        assert order.order_number in mail.outbox[0].body

        if request_has_profile_token:
            # always when profile_token is supplied, fetch customer info from profile
            assert mail.outbox[0].to == [order.lease.application.email]
        else:
            assert mail.outbox[0].to == [order_original_email]

        assert order.order_number in mail.outbox[0].alternatives[0][0]
        assert mail.outbox[0].alternatives[0][1] == "text/html"

        # Assert that the SMS is being sent
        payment_url = payment_provider.get_payment_email_url(
            order, lang=order.lease.application.language
        )
        sms_context = {
            "product_name": order.product.name,
            "due_date": format_date(
                order.due_date, locale=order.lease.application.language
            ),
            "payment_url": payment_url,
        }

        mock_send_sms.assert_called_with(
            NotificationType.SMS_INVOICE_NOTICE,
            sms_context,
            order.customer_phone,
            language=order.lease.application.language,
        )
    else:
        # no profile_token and no contact info
        assert len(executed["data"]["resendOrder"]["failedOrders"]) == 1
        assert (
            "Profile token is required"
            in executed["data"]["resendOrder"]["failedOrders"][0]["error"]
        )
        assert executed["data"]["resendOrder"]["sentOrders"] == []
        # Assert that the SMS is not sent
        mock_send_sms.assert_not_called()


@pytest.mark.parametrize(
    "order", ["berth_order"], indirect=True,
)
def test_resend_order_in_error(
    order: Order,
    superuser_api_client,
    notification_template_orders_approved,
    payment_provider,
):
    order.customer_email = "foo@email.com"
    order.status = OrderStatus.ERROR
    order.lease.status = LeaseStatus.ERROR
    order.lease.save()
    order.save()

    profile_data = {
        "id": to_global_id(ProfileNode, order.customer.id),
        "first_name": order.lease.application.first_name,
        "last_name": order.lease.application.last_name,
        "primary_email": {"email": order.lease.application.email},
        "primary_phone": {"phone": order.lease.application.phone_number},
    }
    variables = {"orders": [to_global_id(OrderNode, order.id)]}

    with mock.patch(
        "requests.post",
        side_effect=mocked_response_profile(
            count=0, data=profile_data, use_edges=False
        ),
    ), mock.patch.object(
        SMSNotificationService, "send", return_value=None
    ) as mock_send_sms:
        executed = superuser_api_client.execute(RESEND_ORDER_MUTATION, input=variables)

    order.refresh_from_db()
    order.lease.refresh_from_db()

    assert executed["data"]["resendOrder"]["sentOrders"] == [str(order.id)]

    assert order.lease.status == LeaseStatus.OFFERED
    assert order.status == OrderStatus.OFFERED

    assert len(mail.outbox) == 1
    assert (
        mail.outbox[0].subject
        == f"test order approved subject, event: {order.order_number}!"
    )
    assert order.order_number in mail.outbox[0].body

    assert mail.outbox[0].to == ["foo@email.com"]

    assert order.order_number in mail.outbox[0].alternatives[0][0]
    assert mail.outbox[0].alternatives[0][1] == "text/html"

    # Assert that the SMS is being sent
    payment_url = payment_provider.get_payment_email_url(
        order, lang=order.lease.application.language
    )
    sms_context = {
        "product_name": order.product.name,
        "due_date": format_date(
            order.due_date, locale=order.lease.application.language
        ),
        "payment_url": payment_url,
    }

    mock_send_sms.assert_called_with(
        NotificationType.SMS_INVOICE_NOTICE,
        sms_context,
        order.customer_phone,
        language=order.lease.application.language,
    )


@pytest.mark.parametrize(
    "order", ["berth_order"], indirect=True,
)
def test_resend_order_not_fixed_in_error(
    order: Order, superuser_api_client, notification_template_orders_approved,
):
    order.status = OrderStatus.ERROR
    order.lease.status = LeaseStatus.ERROR
    order.lease.save()
    order.save()

    profile_data = {
        "id": to_global_id(ProfileNode, order.customer.id),
        "first_name": "Foo",
        "last_name": "Bar",
        "primary_email": {"email": None},
        "primary_phone": {"phone": None},
    }
    variables = {"orders": [to_global_id(OrderNode, order.id)], "profileToken": "token"}

    with mock.patch(
        "requests.post",
        side_effect=mocked_response_profile(
            count=0, data=profile_data, use_edges=False
        ),
    ):
        executed = superuser_api_client.execute(RESEND_ORDER_MUTATION, input=variables)

    order.refresh_from_db()
    order.lease.refresh_from_db()

    assert len(executed["data"]["resendOrder"]["failedOrders"]) == 1
    failed_order = executed["data"]["resendOrder"]["failedOrders"][0]

    assert failed_order["id"] == to_global_id(OrderNode, order.id)
    assert "Missing customer email" in str(failed_order["error"])

    assert order.lease.status == LeaseStatus.ERROR
    assert order.status == OrderStatus.ERROR

    assert len(mail.outbox) == 0


@freeze_time("2020-10-01T08:00:00Z")
@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@pytest.mark.parametrize(
    "order", ["berth_order"], indirect=True,
)
@pytest.mark.parametrize(
    "order_status",
    [
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
        OrderStatus.PAID_MANUALLY,
        OrderStatus.PAID,
    ],
)
def test_resend_order_in_invalid_state(
    api_client, order: Order, notification_template_orders_approved, order_status
):
    order.status = OrderStatus.OFFERED
    order.order_type = OrderType.LEASE_ORDER.value
    order.customer_phone = "+358505658789"
    order.customer_email = "test@kuva.hel.ninja"
    order.save()
    order.lease.status = LeaseStatus.OFFERED
    order.lease.save()
    order.set_status(order_status)  # sets lease status here too
    orders = [order]

    variables = {
        "orders": [to_global_id(OrderNode, o.id) for o in orders],
    }

    executed = api_client.execute(RESEND_ORDER_MUTATION, input=variables)
    assert len(executed["data"]["resendOrder"]["failedOrders"]) == 1
    assert (
        "Cannot resend an invoice for a lease that is not currently offered."
        in executed["data"]["resendOrder"]["failedOrders"][0]["error"]
    )
    assert executed["data"]["resendOrder"]["sentOrders"] == []
