import uuid
from unittest import mock
from unittest.mock import patch

import pytest
from anymail.exceptions import AnymailError
from babel.dates import format_date
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core import mail
from faker import Faker
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from berth_reservations.tests.utils import assert_not_enough_permissions
from customers.services import SMSNotificationService
from customers.tests.conftest import mocked_response_profile
from leases.enums import LeaseStatus
from payments.enums import OrderStatus
from utils.relay import to_global_id

from ..models import Order
from ..notifications import NotificationType
from ..schema.types import OrderNode

APPROVE_ORDER_MUTATION = """
mutation APPROVE_ORDER_MUTATION($input: ApproveOrderMutationInput!) {
    approveOrders(input: $input) {
        failedOrders {
            id
            error
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
def test_approve_order(
    api_client,
    order: Order,
    payment_provider,
    notification_template_orders_approved,
):
    order.status = OrderStatus.DRAFTED
    order.save(update_fields=["status"])

    due_date = (today() + relativedelta(days=14)).date()
    variables = {
        "dueDate": due_date,
        "orders": [
            {
                "orderId": to_global_id(OrderNode, order.id),
                "email": order.lease.application.email,
            }
        ],
    }
    phone = Faker(["fi_FI"]).phone_number()
    order.customer_phone = phone
    order.save()

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=1, data=None, use_edges=False),
    ), mock.patch.object(
        SMSNotificationService, "send", return_value=None
    ) as mock_send_sms:
        executed = api_client.execute(APPROVE_ORDER_MUTATION, input=variables)

    payment_url = payment_provider.get_payment_email_url(
        order, lang=order.lease.application.language
    )

    order = Order.objects.get(id=order.id)

    assert order.due_date == due_date
    assert order.lease.status == LeaseStatus.OFFERED
    assert order.lease.application.status == ApplicationStatus.OFFER_SENT

    assert len(executed["data"]["approveOrders"]["failedOrders"]) == 0
    assert len(mail.outbox) == 1
    assert (
        mail.outbox[0].subject
        == f"test order approved subject, event: {order.order_number}!"
    )
    assert mail.outbox[0].body == f"{ order.order_number } { payment_url }"
    assert mail.outbox[0].to == [order.lease.application.email]

    assert mail.outbox[0].alternatives == [
        (f"<b>{ order.order_number } { payment_url }</b>", "text/html")
    ]

    # Assert that the SMS is being sent
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
        phone,
        language=order.lease.application.language,
    )


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
def test_approve_order_sms_not_sent(
    api_client,
    order: Order,
    payment_provider,
    notification_template_orders_approved,
):
    order.status = OrderStatus.DRAFTED
    order.save(update_fields=["status"])

    order.customer_phone = None
    order.save()

    due_date = (today() + relativedelta(days=14)).date()
    variables = {
        "dueDate": due_date,
        "orders": [
            {
                "orderId": to_global_id(OrderNode, order.id),
                "email": order.lease.application.email,
            }
        ],
    }

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=1, data=None, use_edges=False),
    ), mock.patch.object(
        SMSNotificationService, "send", return_value=None
    ) as mock_send_sms:
        api_client.execute(APPROVE_ORDER_MUTATION, input=variables)

    # Assert that the SMS is not sent
    mock_send_sms.assert_not_called()


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
def test_approve_order_default_due_date(
    api_client,
    order: Order,
    payment_provider,
    notification_template_orders_approved,
):
    order.status = OrderStatus.DRAFTED
    order.save(update_fields=["status"])

    order.due_date = today().date()
    order.save()

    variables = {
        "orders": [
            {
                "orderId": to_global_id(OrderNode, order.id),
                "email": order.lease.application.email,
            }
        ],
    }
    expected_due_date = today().date() + relativedelta(weeks=2)
    assert order.due_date != expected_due_date

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=1, data=None, use_edges=False),
    ):
        api_client.execute(APPROVE_ORDER_MUTATION, input=variables)

    order = Order.objects.get(id=order.id)

    assert order.due_date == expected_due_date


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_approve_order_not_enough_permissions(api_client):
    variables = {
        "orders": [],
    }

    executed = api_client.execute(APPROVE_ORDER_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


@freeze_time("2020-01-01T08:00:00Z")
def test_approve_order_does_not_exist(
    superuser_api_client,
    payment_provider,
    notification_template_orders_approved,
):
    order_id = to_global_id(OrderNode, uuid.uuid4())

    variables = {
        "orders": [{"orderId": order_id, "email": "foo@bar.com"}],
    }

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=1, data=None, use_edges=False),
    ):
        executed = superuser_api_client.execute(APPROVE_ORDER_MUTATION, input=variables)

    assert len(executed["data"]["approveOrders"]["failedOrders"]) == 1
    assert executed["data"]["approveOrders"]["failedOrders"][0] == {
        "id": order_id,
        "error": "Order matching query does not exist.",
    }


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_approve_order_anymail_error(
    superuser_api_client,
    payment_provider,
    notification_template_orders_approved,
    order: Order,
):
    order.status = OrderStatus.DRAFTED
    order.save(update_fields=["status"])

    order_id = to_global_id(OrderNode, order.id)
    previous_order_status = order.status
    previous_lease_status = order.lease.status
    previous_application_status = order.lease.application.status

    variables = {
        "orders": [{"orderId": order_id, "email": "foo@bar.com"}],
    }

    with patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=1, data=None, use_edges=False),
    ):
        with patch(
            "payments.utils.send_notification",
            side_effect=AnymailError("Anymail error"),
        ) as mock:
            executed = superuser_api_client.execute(
                APPROVE_ORDER_MUTATION, input=variables
            )

    mock.assert_called_once()

    assert len(executed["data"]["approveOrders"]["failedOrders"]) == 1
    assert executed["data"]["approveOrders"]["failedOrders"][0] == {
        "id": order_id,
        "error": "Anymail error",
    }

    order = Order.objects.get(id=order.id)

    assert order.status == previous_order_status
    assert order.lease.status == previous_lease_status.value
    assert order.lease.application.status == previous_application_status


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_approve_order_one_success_one_failure(
    superuser_api_client,
    order: Order,
    payment_provider,
    notification_template_orders_approved,
):
    order.status = OrderStatus.DRAFTED
    order.save(update_fields=["status"])

    due_date = (today() + relativedelta(days=14)).date()
    failure_order_id = to_global_id(OrderNode, uuid.uuid4())

    variables = {
        "dueDate": due_date,
        "orders": [
            {"orderId": failure_order_id, "email": "foo@bar.com"},
            {
                "orderId": to_global_id(OrderNode, order.id),
                "email": order.lease.application.email,
            },
        ],
    }

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=1, data=None, use_edges=False),
    ):
        executed = superuser_api_client.execute(APPROVE_ORDER_MUTATION, input=variables)

    payment_url = payment_provider.get_payment_email_url(
        order, lang=order.lease.application.language
    )

    order = Order.objects.get(id=order.id)

    assert len(executed["data"]["approveOrders"]["failedOrders"]) == 1
    assert executed["data"]["approveOrders"]["failedOrders"][0] == {
        "id": failure_order_id,
        "error": "Order matching query does not exist.",
    }

    assert order.due_date == due_date
    assert order.lease.status == LeaseStatus.OFFERED
    assert order.lease.application.status == ApplicationStatus.OFFER_SENT

    assert len(mail.outbox) == 1
    assert (
        mail.outbox[0].subject
        == f"test order approved subject, event: {order.order_number}!"
    )
    assert mail.outbox[0].body == f"{ order.order_number } { payment_url }"
    assert mail.outbox[0].to == [order.lease.application.email]

    assert mail.outbox[0].alternatives == [
        (f"<b>{ order.order_number } { payment_url }</b>", "text/html")
    ]
