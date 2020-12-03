import uuid
from unittest import mock
from unittest.mock import patch

import pytest
from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core import mail
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from berth_reservations.tests.constants import MOCK_PROFILE_TOKEN_SERVICE
from berth_reservations.tests.utils import assert_not_enough_permissions
from customers.tests.conftest import mocked_response_profile
from leases.enums import LeaseStatus
from utils.relay import to_global_id

from ..models import Order
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
    "api_client", ["berth_services"], indirect=True,
)
@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_approve_order(
    api_client, order: Order, payment_provider, notification_template_orders_approved,
):
    api_client.execute_options["context"].META[
        "HTTP_API_TOKENS"
    ] = f'{{"{MOCK_PROFILE_TOKEN_SERVICE}": "token"}}'

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
    ):
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


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_approve_order_default_due_date(
    api_client, order: Order, payment_provider, notification_template_orders_approved,
):
    api_client.execute_options["context"].META[
        "HTTP_API_TOKENS"
    ] = f'{{"{MOCK_PROFILE_TOKEN_SERVICE}": "token"}}'

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
    superuser_api_client, payment_provider, notification_template_orders_approved,
):
    superuser_api_client.execute_options["context"].META[
        "HTTP_API_TOKENS"
    ] = f'{{"{MOCK_PROFILE_TOKEN_SERVICE}": "token"}}'

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
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_approve_order_anymail_error(
    superuser_api_client,
    payment_provider,
    notification_template_orders_approved,
    order: Order,
):
    superuser_api_client.execute_options["context"].META[
        "HTTP_API_TOKENS"
    ] = f'{{"{MOCK_PROFILE_TOKEN_SERVICE}": "token"}}'

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
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_approve_order_one_success_one_failure(
    superuser_api_client,
    order: Order,
    payment_provider,
    notification_template_orders_approved,
):
    superuser_api_client.execute_options["context"].META[
        "HTTP_API_TOKENS"
    ] = f'{{"{MOCK_PROFILE_TOKEN_SERVICE}": "token"}}'

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
