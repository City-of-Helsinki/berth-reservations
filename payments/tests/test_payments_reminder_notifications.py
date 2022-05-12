import datetime
from unittest import mock

import pytest
import pytz
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from customers.services import SMSNotificationService
from payments.enums import OrderStatus
from payments.models import Order


@freeze_time("2020-10-20T08:00:00Z")
@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True
)
@pytest.mark.parametrize(
    "notification_sent,until_due_date,should_be_sent",
    [
        (None, 8, False),
        (None, 7, True),
        (None, 6, True),
        (None, 3, True),
        (None, 1, True),
        (None, -1, False),
        # 7 days before and after
        (datetime.datetime(2020, 10, 19, 7), 8, False),  # Before 7 day threshold
        (datetime.datetime(2020, 10, 19, 7), 7, True),  # Should send 7 day reminder
        (datetime.datetime(2020, 10, 20, 7), 7, False),  # Already sent 7 day reminder
        (datetime.datetime(2020, 10, 18, 7), 6, True),  # Should send 7 day reminder
        (datetime.datetime(2020, 10, 20, 7), 6, False),  # Already sent 7 day reminder
        # 3 days before and after
        (datetime.datetime(2020, 10, 19, 7), 3, True),  # Should send 3 day reminder
        (datetime.datetime(2020, 10, 20, 7), 3, False),  # Already sent 3 day reminder
        (datetime.datetime(2020, 10, 18, 7), 2, True),  # Should send 3 day reminder
        (datetime.datetime(2020, 10, 20, 7), 2, False),  # Already sent 3 day reminder
        # 1 days before and after
        (datetime.datetime(2020, 10, 19, 7), 1, True),  # Should send 1 day reminder
        (datetime.datetime(2020, 10, 20, 7), 1, False),  # Already sent 1 day reminder
        (datetime.datetime(2020, 10, 18, 7), 0, True),  # Should send 1 day reminder
        (datetime.datetime(2020, 10, 20, 7), 0, False),  # Already sent 1 day reminder
        # Past due date
        (datetime.datetime(2020, 10, 1, 7), -1, False),
    ],
)
def test_payment_reminder_is_sent(
    notification_sent,
    until_due_date,
    should_be_sent,
    order: Order,
    notification_template_orders_approved,
):
    """A payment reminder should be sent 7, 3 and 1 days before the due date."""
    sent_timestamp = (
        notification_sent.replace(tzinfo=pytz.UTC) if notification_sent else None
    )

    order.payment_notification_sent = sent_timestamp
    order.status = OrderStatus.OFFERED
    order.due_date = timezone.localdate() + datetime.timedelta(days=until_due_date)
    order.save()

    with mock.patch.object(
        SMSNotificationService, "send", return_value=None
    ) as mock_send_sms:
        changes = Order.objects.send_payment_reminders_for_unpaid_orders()

    order = Order.objects.get(pk=order.pk)

    if should_be_sent:
        assert order.payment_notification_sent == timezone.now()
        assert changes == 1
        assert len(mail.outbox) == 1
        mock_send_sms.assert_called_once()
    else:
        assert order.payment_notification_sent == sent_timestamp
        assert changes == 0
        assert len(mail.outbox) == 0
        mock_send_sms.assert_not_called()
