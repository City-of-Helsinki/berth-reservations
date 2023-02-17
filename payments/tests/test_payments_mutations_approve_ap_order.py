from unittest import mock
from requests import Session

import pytest
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core import mail
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from customers.services import SMSNotificationService
from customers.tests.conftest import MOCK_HKI_PROFILE_ADDRESS, mocked_response_profile
from leases.enums import LeaseStatus
from payments.enums import OrderStatus
from utils.relay import to_global_id

from ..enums import ProductServiceType
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
    ["additional_product_order_with_lease_order"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_approve_ap_order(
    api_client,
    order: Order,
    bambora_payment_provider,
    notification_template_orders_approved,
):
    order.status = OrderStatus.DRAFTED
    order.save(update_fields=["status"])

    due_date = (today() + relativedelta(days=14)).date()
    email = "foo@bar.com"
    variables = {
        "dueDate": str(due_date),
        "orders": [{"orderId": to_global_id(OrderNode, order.id), "email": email}],
        "profileToken": "mock_token",
    }

    with mock.patch.object(Session,
                           "post",
                           side_effect=mocked_response_profile(count=1, data=None, use_edges=False),
                           ), mock.patch.object(
        SMSNotificationService, "send", return_value=None
    ) as mock_send_sms:
        executed = api_client.execute(APPROVE_ORDER_MUTATION, input=variables)

    payment_url = bambora_payment_provider.get_payment_email_url(
        order, lang=order.lease.application.language
    )

    order = Order.objects.get(id=order.id)

    assert order.due_date == due_date

    # approving additional product order should not touch the lease
    assert order.lease.status != LeaseStatus.OFFERED
    assert order.lease.application.status != ApplicationStatus.OFFER_SENT

    # customer data should be filled
    assert len(order.customer_first_name) > 0
    assert len(order.customer_last_name) > 0
    assert len(order.customer_email) > 0
    assert order.customer_address == MOCK_HKI_PROFILE_ADDRESS.get("address")
    assert order.customer_zip_code == MOCK_HKI_PROFILE_ADDRESS.get("postal_code")
    assert order.customer_city == MOCK_HKI_PROFILE_ADDRESS.get("city")

    assert len(executed["data"]["approveOrders"]["failedOrders"]) == 0
    assert len(mail.outbox) == 1
    assert (
        mail.outbox[0].subject
        == f"test order approved subject, event: {order.order_number}!"
    )
    assert mail.outbox[0].body == f"{ order.order_number } { payment_url }"
    assert mail.outbox[0].to == [email]

    assert mail.outbox[0].alternatives == [
        (f"<b>{ order.order_number } { payment_url }</b>", "text/html")
    ]
    product_name = ", ".join(
        [
            str(ProductServiceType(order_line.product.service).label)
            for order_line in order.order_lines.all()
        ]
    )
    # Assert that the SMS is being sent
    sms_context = {
        "order": order,
        "product_name": product_name,
        "payment_url": payment_url,
        "include_berth": True,
    }

    mock_send_sms.assert_called_with(
        NotificationType.SMS_INVOICE_NOTICE,
        sms_context,
        order.customer_phone,
        language=order.lease.application.language,
    )
