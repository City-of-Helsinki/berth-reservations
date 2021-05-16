import datetime

import pytest  # noqa
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from leases.enums import LeaseStatus
from payments.enums import OrderStatus
from payments.models import Order
from payments.tests.factories import OrderFactory


@freeze_time("2021-01-09T08:00:00Z")
def test_expire_too_old_unpaid_orders(berth_lease):
    # VEN-783:
    # The due date should only be editable up to 7 days after it has expired.
    # Therefore invalidated orders should be expired when due date + 7 days have gone.
    order = OrderFactory(
        lease=berth_lease,
        due_date=datetime.date(2021, 1, 2),
        status=OrderStatus.OFFERED,
    )
    assert (
        Order.objects.expire_too_old_unpaid_orders(older_than_days=7, dry_run=False)
        == 0
    )
    order.refresh_from_db()
    assert order.status == OrderStatus.OFFERED
    order.due_date = datetime.date(2021, 1, 1)
    order.save()

    assert (
        Order.objects.expire_too_old_unpaid_orders(older_than_days=7, dry_run=False)
        == 1
    )

    order.refresh_from_db()
    order.lease.refresh_from_db()
    assert order.status == OrderStatus.EXPIRED
    assert order.lease.status == LeaseStatus.EXPIRED
    assert len(order.log_entries.all()) == 1
    assert "Order expired at 2021-01-02" in order.log_entries.first().comment
    # VEN-783: "After that, it should not be possible to modify, and the API should return an error."
    order.due_date = datetime.datetime(2021, 2, 1)
    with pytest.raises(ValidationError):
        order.save()
