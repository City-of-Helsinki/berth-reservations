import pytest
from dateutil.utils import today
from django.core import mail
from django.test import RequestFactory

from applications.enums import ApplicationStatus
from leases.enums import LeaseStatus
from payments.utils import approve_order


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_approve_order(order, payment_provider, notification_template_orders_approved):
    request = RequestFactory().request()
    due_date = today().date()
    approve_order(order, order.lease.application.email, due_date, request)

    order.refresh_from_db()

    assert order.due_date == due_date
    assert order.lease.status == LeaseStatus.OFFERED
    assert order.lease.application.status == ApplicationStatus.OFFER_SENT

    payment_url = payment_provider.get_payment_email_url(
        order, lang=order.lease.application.language
    )

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
