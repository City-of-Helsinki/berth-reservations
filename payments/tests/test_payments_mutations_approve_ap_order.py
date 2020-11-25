import pytest
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core import mail
from freezegun import freeze_time

from applications.enums import ApplicationStatus
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
    "order", ["additional_product_order"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_approve_ap_order(
    api_client, order: Order, payment_provider, notification_template_orders_approved,
):
    due_date = (today() + relativedelta(days=14)).date()
    email = "foo@bar.com"
    variables = {
        "dueDate": due_date,
        "orders": [{"orderId": to_global_id(OrderNode, order.id), "email": email}],
    }
    executed = api_client.execute(APPROVE_ORDER_MUTATION, input=variables)
    payment_url = payment_provider.get_payment_email_url(order, lang="en")

    order = Order.objects.get(id=order.id)

    assert order.due_date == due_date

    # approving additional product order should not touch the lease
    assert order.lease.status != LeaseStatus.OFFERED
    assert order.lease.application.status != ApplicationStatus.OFFER_SENT

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
